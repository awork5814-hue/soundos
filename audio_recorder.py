import io
import wave
import numpy as np
import sounddevice as sd
import config

class AudioRecorder:
    def __init__(self):
        self.sample_rate = getattr(config, "SAMPLE_RATE", 16000)
        self.channels = getattr(config, "CHANNELS", 1)
        self.is_recording = False
        self.frames = []
        self.stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """دالة داخلية تستقبل بيانات الصوت الحية من المايك أثناء التسجيل"""
        if self.is_recording:
            self.frames.append(indata.copy())

    def start(self):
        """بدء تسجيل الصوت من المايكروفون"""
        if self.is_recording:
            return
        self.frames = []
        self.is_recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._audio_callback
        )
        self.stream.start()

    def stop(self) -> bytes:
        """
        إيقاف التسجيل وتحويل البيانات الصوتية إلى بايتات WAV في الذاكرة (RAM) مباشرة
        دون إنشاء أي ملفات مؤقتة على القرص الصلب.
        """
        if not self.is_recording:
            return b""

        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.frames:
            return b""

        audio_data = np.concatenate(self.frames, axis=0)
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit PCM = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return wav_buffer.getvalue()
