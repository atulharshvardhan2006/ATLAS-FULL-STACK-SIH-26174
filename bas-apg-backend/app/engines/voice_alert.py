"""
BAS-APG — Background TTS Voice Alert Worker

Provides offline text-to-speech using pyttsx3 in a dedicated background thread.

CRITICAL IMPLEMENTATION DETAILS:
  1. pyttsx3.init() MUST be called INSIDE the worker thread
     (macOS NSRunLoop conflicts if called in the main thread)
  2. engine.runAndWait() BLOCKS — this is why it needs its own thread
  3. The queue provides backpressure — messages play sequentially
  4. daemon=True ensures the thread dies when the app exits

macOS: Uses NSSpeechSynthesizer (built-in, no download needed)
"""

import queue
import threading

class BackgroundTTSWorker(threading.Thread):
    """Threaded TTS worker that speaks messages without blocking FastAPI.

    Usage:
        tts = BackgroundTTSWorker(rate=160)
        tts.start()
        tts.speak("Step 1 confirmed")  # Returns immediately
        tts.stop()                      # Graceful shutdown
    """

    def __init__(self, rate: int = 160, enabled: bool = True):
        super().__init__(daemon=True)
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._rate = rate
        self._enabled = enabled
        self._running = False

    def run(self):
        """Main TTS loop — runs in background thread."""
        if not self._enabled:
            print("[TTS] Voice alerts disabled.")
            self._running = True
            
            while self._running:
                try:
                    text = self._queue.get(timeout=1.0)
                    if text is None:
                        break
                except queue.Empty:
                    continue
            return

        try:
            import pyttsx3  

            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)

            
            voices = engine.getProperty("voices")
            for voice in voices:
                vid = voice.id.lower()
                if "alex" in vid or "samantha" in vid or "daniel" in vid:
                    engine.setProperty("voice", voice.id)
                    print(f"[TTS] Using voice: {voice.id}")
                    break

            self._running = True
            print(f"[TTS] Voice alert worker started (rate={self._rate} WPM)")

            while self._running:
                try:
                    text = self._queue.get(timeout=0.5)

                    if text is None:
                        
                        break

                    print(f"[TTS] Speaking: {text[:80]}...")
                    engine.say(text)
                    engine.runAndWait()

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[TTS] Error during speech: {e}")

            engine.stop()
            print("[TTS] Voice alert worker stopped.")

        except ImportError:
            print("[TTS] pyttsx3 not installed — voice alerts disabled")
            self._running = True
            while self._running:
                try:
                    text = self._queue.get(timeout=1.0)
                    if text is None:
                        break
                except queue.Empty:
                    continue
        except Exception as e:
            print(f"[TTS] Failed to initialize: {e}")
            self._running = True

    def speak(self, text: str):
        """Queue a message for TTS. Returns immediately (non-blocking).

        If the worker is already speaking, messages queue up and play in order.
        """
        if self._running:
            self._queue.put(text)

    def stop(self):
        """Signal the worker to shut down gracefully."""
        self._running = False
        self._queue.put(None)  
