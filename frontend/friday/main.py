import asyncio
import signal
import sys
import threading
from typing import Any

import numpy as np

from friday.config import get_config, Config
from friday.utils.logging import setup_logging, get_logger
from friday.cloud.client import CloudClient
from friday.cloud.auth import AuthManager
from friday.audio.wake_word import WakeWordDetector, MockWakeWordDetector
from friday.audio.listener import AudioListener
from friday.audio.stt import SpeechToText
from friday.audio.tts import TextToSpeech, MockTextToSpeech
from friday.brain.llm import LLMClient
from friday.brain.memory import MemoryManager
from friday.brain.prompts import PromptBuilder


logger = get_logger(__name__)


class FridayAssistant:
    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        setup_logging(self.config.log_level, self.config.log_file or None)

        # Components
        self.auth = AuthManager()
        self.cloud = CloudClient(self.auth)
        self.llm = LLMClient()
        self.memory_manager = MemoryManager(self.cloud, self.llm)
        self.prompt_builder = PromptBuilder()

        # Audio components
        self.stt = SpeechToText()
        self._init_tts()
        self.listener = AudioListener()
        self._init_wake_word()

        # State
        self._running = False
        self._processing = False
        self._current_conversation_id: str | None = None
        self._conversation_history: list[dict[str, str]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def _init_tts(self):
        if self.config.tts.model_path:
            self.tts = TextToSpeech()
        else:
            logger.warning("TTS model not configured, using mock TTS")
            self.tts = MockTextToSpeech()

    def _init_wake_word(self):
        if self.config.audio.porcupine_access_key:
            try:
                self.wake_word = WakeWordDetector(callback=self._on_wake_word)
            except Exception as e:
                logger.warning(f"Failed to init wake word detector: {e}, using mock")
                self.wake_word = MockWakeWordDetector(callback=self._on_wake_word)
        else:
            logger.warning("Porcupine key not configured, using mock wake word detector")
            self.wake_word = MockWakeWordDetector(callback=self._on_wake_word)

    def _on_wake_word(self):
        """Called when wake word is detected"""
        if self._processing:
            return

        logger.info("Wake word detected, starting interaction")
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._handle_interaction(), self._loop)

    async def _handle_interaction(self):
        """Handle a complete voice interaction"""
        if self._processing:
            return

        self._processing = True
        try:
            # Play activation sound (if available)
            # self.tts.speak("Yes?", blocking=True)

            # Start recording
            audio_future = asyncio.Future()

            def on_recording_complete(audio_data: np.ndarray):
                if not audio_future.done():
                    self._loop.call_soon_threadsafe(
                        audio_future.set_result, audio_data
                    )

            self.listener.start_recording(on_complete=on_recording_complete)

            # Wait for audio
            try:
                audio_data = await asyncio.wait_for(audio_future, timeout=35.0)
            except asyncio.TimeoutError:
                logger.warning("Recording timed out")
                self.listener.stop_recording()
                return

            if audio_data is None or len(audio_data) < self.config.audio.sample_rate * 0.3:
                logger.warning("Audio too short, ignoring")
                return

            # Transcribe
            logger.info("Transcribing audio...")
            text = self.stt.transcribe(audio_data, self.config.audio.sample_rate)

            if not text or len(text.strip()) < 2:
                logger.warning("Empty or too short transcription")
                return

            logger.info(f"User said: {text}")

            # Generate response
            response = await self._generate_response(text)

            if response:
                logger.info(f"Friday: {response}")
                self.tts.speak(response, blocking=True)

                # Save to cloud
                await self._save_exchange(text, response)

        except Exception as e:
            logger.error(f"Interaction error: {e}")
        finally:
            self._processing = False

    async def _generate_response(self, user_message: str) -> str:
        """Generate response using LLM"""
        # Search for relevant memories
        relevant_memories = await self.memory_manager.search_relevant_memories(
            user_message, limit=5
        )
        if relevant_memories:
            self.prompt_builder.set_memories(relevant_memories)

        # Build messages
        messages = self.prompt_builder.build_chat_messages(
            self._conversation_history,
            user_message,
        )

        # Generate response
        response = await self.llm.generate(messages, stream=False)
        return response

    async def _save_exchange(self, user_message: str, assistant_response: str):
        """Save the exchange to cloud"""
        try:
            # Create conversation if needed
            if not self._current_conversation_id:
                conv = await self.cloud.create_conversation()
                if conv:
                    self._current_conversation_id = conv["id"]

            if self._current_conversation_id:
                # Save messages
                await self.cloud.add_message(
                    self._current_conversation_id,
                    "user",
                    user_message,
                )
                await self.cloud.add_message(
                    self._current_conversation_id,
                    "assistant",
                    assistant_response,
                )

            # Update local history
            self._conversation_history.append({"role": "user", "content": user_message})
            self._conversation_history.append({"role": "assistant", "content": assistant_response})

            # Trim history if too long
            if len(self._conversation_history) > 20:
                self._conversation_history = self._conversation_history[-20:]

            # Periodically extract memories
            if len(self._conversation_history) >= 6 and len(self._conversation_history) % 6 == 0:
                await self.memory_manager.extract_and_store_memories(
                    self._conversation_history[-6:],
                    self._current_conversation_id,
                )

        except Exception as e:
            logger.error(f"Failed to save exchange: {e}")

    async def _setup_hotkey(self):
        """Setup keyboard hotkey"""
        try:
            import keyboard

            def on_hotkey():
                logger.info("Hotkey pressed")
                self._on_wake_word()

            keyboard.add_hotkey(self.config.hotkey, on_hotkey)
            logger.info(f"Hotkey '{self.config.hotkey}' registered")
        except ImportError:
            logger.warning("keyboard module not available, hotkey disabled")
        except Exception as e:
            logger.warning(f"Failed to setup hotkey: {e}")

    async def start(self):
        """Start the assistant"""
        logger.info("Starting Friday AI Assistant...")

        # Check cloud connection
        if not await self.cloud.health_check():
            logger.warning("Cloud server not available, running in offline mode")
        else:
            # Try to authenticate
            if not self.auth.is_authenticated:
                if self.config.cloud.username and self.config.cloud.password:
                    await self.auth.login()

            # Load memories
            if self.auth.is_authenticated:
                await self.memory_manager.load_memories()

        # Check LLM
        if not await self.llm.check_health():
            logger.error("Ollama not available. Please start Ollama first.")
            return

        self._running = True
        self._loop = asyncio.get_event_loop()

        # Start wake word detection
        self.wake_word.start()

        # Setup hotkey
        await self._setup_hotkey()

        logger.info("Friday is ready! Say the wake word or press the hotkey.")

        # Main loop
        try:
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    def stop(self):
        """Stop the assistant"""
        logger.info("Stopping Friday...")
        self._running = False

        self.wake_word.stop()
        self.listener.stop_recording()
        self.tts.stop()

        logger.info("Friday stopped")


def main():
    """Main entry point"""
    assistant = FridayAssistant()

    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        assistant.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    try:
        asyncio.run(assistant.start())
    except KeyboardInterrupt:
        assistant.stop()


if __name__ == "__main__":
    main()
