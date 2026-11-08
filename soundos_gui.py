import io
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import ollama

# 1. Initialize Faster-Whisper (quantized int8 for fast CPU inference)
whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

audio_queue = queue.Queue()
stop_listening = threading.Event()

def audio_callback(indata, frames, time_info, status):
    if status:
        pass
    audio_queue.put(indata.copy())

def rule_based_fallback(text):
    """Zero-latency regex engine for common operations."""
    t = text.lower().strip().rstrip(".")

    # Python file with greeting function
    if "python" in t and ("greeting" in t or "greet" in t):
        return (
            "cat << 'EOF' > ~/greeting.py\n"
            "def greeting(name='User'):\n"
            "    print(f'Hello, {name}!')\n\n"
            "if __name__ == '__main__':\n"
            "    greeting()\n"
            "EOF"
        )

    # Specific named python file
    m = re.search(r'(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?python\s+file(?:\s+(?:named|called))?\s+([a-zA-Z0-9_\-]+)(?:\.py)?', t)
    if m:
        return f"touch ~/{m.group(1)}.py"

    # Generic python file
    if re.search(r'^(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?python\s+file', t):
        return "touch ~/main.py"

    # Folders on Desktop
    m = re.search(r'(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)(?:\s+(?:named|called|and\s+name\s+it))?\s+([a-zA-Z0-9_\-\.]+)\s+(?:on|in|to)\s+(?:the\s+)?desktop', t)
    if m:
        return f"mkdir -p ~/Desktop/{m.group(1)}"

    # Folders in Home
    m = re.search(r'(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)(?:\s+(?:named|called|and\s+name\s+it))?\s+([a-zA-Z0-9_\-\.]+)', t)
    if m:
        return f"mkdir -p ~/{m.group(1)}"

    # Files on Desktop
    m = re.search(r'(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+|called\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:on|in|to)\s+(?:the\s+)?desktop', t)
    if m:
        return f"touch ~/Desktop/{m.group(1)}"

    # Files in Home
    m = re.search(r'(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+|called\s+)?([a-zA-Z0-9_\-\.]+)', t)
    if m:
        return f"touch ~/{m.group(1)}"

    # Delete
    m = re.search(r'(?:delete|remove)\s+(?:the\s+)?(?:file|folder|directory)\s+([a-zA-Z0-9_\-\.]+)', t)
    if m:
        return f"rm -rf ~/{m.group(1)}"

    # System queries
    if any(k in t for k in ["list files", "show files", "list directory"]):
        return "ls -la ~"
    if "date" in t or "day" in t:
        return "date"
    if "who am i" in t or "current user" in t:
        return "whoami"
    if "ip address" in t:
        return "hostname -I"

    return None

def clean_llm_output(raw_text):
    """Extracts raw bash code from markdown or strips conversational lines."""
    code_match = re.search(r'```(?:bash|sh)?\s*(.*?)\s*```', raw_text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    filtered = []
    for line in raw_text.splitlines():
        l_strip = line.strip()
        if l_strip.endswith(":") and any(w in l_strip.lower() for w in ["command", "following", "script"]):
            continue
        if re.match(r'^(to\s|you\s|here\s|sure\s|note\s|this\s|in\sorder)', l_strip, re.IGNORECASE):
            continue
        filtered.append(line)

    return "\n".join(filtered).strip().strip("`").strip()

def extract_command_llm(user_text):
    quick = rule_based_fallback(user_text)
    if quick:
        return quick

    prompt = f"""You are a Linux command translation tool.
Output ONLY the raw executable bash command or script.
Do not provide explanations, markdown links, or introductory greetings.

Task: {user_text}
Bash:"""

    try:
        response = ollama.generate(
            model="qwen2.5-coder:1.5b",
            prompt=prompt,
            options={
                "temperature": 0.0,
                "num_predict": 128,
                "stop": ["Task:", "User:"]
            }
        )
        raw_output = response.get("response", "").strip()
        cleaned = clean_llm_output(raw_output)
        return cleaned if cleaned else f"echo 'Could not translate: {user_text}'"
    except Exception as e:
        return f"echo 'Ollama Error: {e}'"

class SoundOSGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SoundOS — Voice Terminal Assistant")
        self.geometry("720x620")
        self.minsize(550, 480)
        self.configure(bg="#1e1e2e")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.is_listening = False
        self.build_ui()

    def build_ui(self):
        # Header / Status bar
        header_frame = tk.Frame(self, bg="#1e1e2e")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        self.status_label = tk.Label(
            header_frame,
            text="● Idle (Click 'Start Recording' and speak)",
            fg="#a6adc8",
            bg="#1e1e2e",
            font=("Ubuntu", 11, "bold")
        )
        self.status_label.pack(side="left")

        self.mic_button = tk.Button(
            header_frame,
            text="🎙 Start Recording",
            command=self.toggle_listening,
            bg="#89b4fa",
            fg="#11111b",
            font=("Ubuntu", 10, "bold"),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        self.mic_button.pack(side="right")

        # 1. Voice Recognition Entry
        speech_frame = tk.LabelFrame(
            self,
            text=" 1. Voice Recognition (Editable) ",
            fg="#cdd6f4",
            bg="#181825",
            font=("Ubuntu", 10, "bold"),
            padx=10,
            pady=8
        )
        speech_frame.pack(fill="x", padx=15, pady=6)

        self.speech_entry = tk.Entry(
            speech_frame,
            font=("Ubuntu Mono", 11),
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat"
        )
        self.speech_entry.pack(fill="x", pady=(0, 6), ipady=4)
        self.speech_entry.bind("<Return>", lambda e: self.generate_command_action())

        btn_gen = tk.Button(
            speech_frame,
            text="⚡ Translate to Bash",
            command=self.generate_command_action,
            bg="#a6e3a1",
            fg="#11111b",
            font=("Ubuntu", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_gen.pack(anchor="e")

        # 2. Bash Command Entry
        cmd_frame = tk.LabelFrame(
            self,
            text=" 2. Proposed Bash Command (Editable) ",
            fg="#cdd6f4",
            bg="#181825",
            font=("Ubuntu", 10, "bold"),
            padx=10,
            pady=8
        )
        cmd_frame.pack(fill="x", padx=15, pady=6)

        self.cmd_box = tk.Text(
            cmd_frame,
            font=("Ubuntu Mono", 11, "bold"),
            bg="#313244",
            fg="#f9e2af",
            insertbackground="#f9e2af",
            relief="flat",
            height=6
        )
        self.cmd_box.pack(fill="x", pady=(0, 6))

        btn_exec = tk.Button(
            cmd_frame,
            text="▶ Execute Command",
            command=self.execute_action,
            bg="#fab387",
            fg="#11111b",
            font=("Ubuntu", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_exec.pack(anchor="e")

        # 3. Execution Log Box
        log_frame = tk.LabelFrame(
            self,
            text=" 3. Execution Log & Terminal Output ",
            fg="#cdd6f4",
            bg="#181825",
            font=("Ubuntu", 10, "bold"),
            padx=10,
            pady=8
        )
        log_frame.pack(fill="both", expand=True, padx=15, pady=(6, 15))

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            font=("Ubuntu Mono", 10),
            bg="#11111b",
            fg="#a6adc8",
            relief="flat",
            height=6
        )
        self.log_box.pack(fill="both", expand=True)

    def log(self, text):
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")

    def toggle_listening(self):
        if not self.is_listening:
            self.is_listening = True
            stop_listening.clear()
            self.mic_button.configure(text="🛑 Stop & Transcribe", bg="#f38ba8")
            self.status_label.configure(text="● Recording voice...", fg="#a6e3a1")
            self.log("[Mic]: Recording started...")
            threading.Thread(target=self._record_thread, daemon=True).start()
        else:
            self.is_listening = False
            stop_listening.set()
            self.mic_button.configure(text="🎙 Start Recording", bg="#89b4fa")
            self.status_label.configure(text="● Transcribing audio...", fg="#f9e2af")

    def _record_thread(self):
        sample_rate = 16000
        recorded_chunks = []
        while not audio_queue.empty():
            audio_queue.get_nowait()

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                callback=audio_callback
            ):
                while not stop_listening.is_set():
                    try:
                        chunk = audio_queue.get(timeout=0.1)
                        recorded_chunks.append(chunk)
                    except queue.Empty:
                        continue
        except Exception as e:
            self.after(0, self.log, f"[Mic Error]: {e}")
            self.after(0, self._reset_mic_ui)
            return

        if not recorded_chunks:
            self.after(0, self._reset_mic_ui)
            return

        audio_data = np.concatenate(recorded_chunks, axis=0).flatten()

        if len(audio_data) < sample_rate * 0.5:
            self.after(0, self.log, "[Mic]: Audio snippet too short.")
            self.after(0, self._reset_mic_ui)
            return

        try:
            segments, _ = whisper_model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                vad_filter=True
            )
            transcribed_text = " ".join([seg.text.strip() for seg in segments]).strip()
            if transcribed_text:
                self.after(0, self._on_transcribed, transcribed_text)
            else:
                self.after(0, self.log, "[Whisper]: No speech detected.")
        except Exception as e:
            self.after(0, self.log, f"[Whisper Error]: {e}")
        finally:
            self.after(0, self._reset_mic_ui)

    def _reset_mic_ui(self):
        self.is_listening = False
        self.mic_button.configure(text="🎙 Start Recording", bg="#89b4fa")
        self.status_label.configure(text="● Idle", fg="#a6adc8")

    def _on_transcribed(self, text):
        self.speech_entry.delete(0, "end")
        self.speech_entry.insert(0, text)
        self.log(f"[Whisper Recognized]: \"{text}\"")
        self.generate_command_action()

    def generate_command_action(self):
        user_text = self.speech_entry.get().strip()
        if not user_text:
            return
        self.status_label.configure(text="● Translating with Qwen Coder...", fg="#f9e2af")
        threading.Thread(target=self._generate_thread, args=(user_text,), daemon=True).start()

    def _generate_thread(self, user_text):
        cmd = extract_command_llm(user_text)
        self.after(0, self._on_cmd_ready, cmd)

    def _on_cmd_ready(self, cmd):
        self.cmd_box.delete("1.0", "end")
        self.cmd_box.insert("1.0", cmd)
        self.status_label.configure(text="● Ready to execute", fg="#89b4fa")
        self.log(f"[Proposed Command]:\n{cmd}")

    def execute_action(self):
        cmd = self.cmd_box.get("1.0", "end").strip()
        if not cmd:
            return
        self.log(f"\n$ Executing command...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                text=True,
                capture_output=True
            )
            if result.stdout:
                self.log(result.stdout.strip())
            self.log("[Success]")
        except subprocess.CalledProcessError as err:
            if err.stderr:
                self.log(f"[Error]: {err.stderr.strip()}")
            else:
                self.log(f"[Error]: Return code {err.returncode}")

if __name__ == "__main__":
    app = SoundOSGUI()
    app.mainloop()
