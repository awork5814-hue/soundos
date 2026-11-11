import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import config
from audio_recorder import AudioRecorder
from ai_engine import AIEngine
import context_scanner
import executor


class SoundOSApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SoundOS — Voice-Controlled Linux Assistant")
        self.root.geometry("680x560")
        self.root.configure(bg="#1e1e2e")

        self.recorder = AudioRecorder()
        self.ai_engine = None
        self.is_recording = False
        self.current_command = ""

        self._build_api_page()

    # ------------------------------------------------------------------
    # الصفحة الأولى: إدخال مفتاح الـ API Key
    # ------------------------------------------------------------------
    def _build_api_page(self):
        self._clear_window()

        frame = tk.Frame(self.root, bg="#1e1e2e", padx=30, pady=40)
        frame.pack(expand=True, fill="both")

        tk.Label(
            frame, text="🎙️ SoundOS", font=("Arial", 24, "bold"),
            fg="#89b4fa", bg="#1e1e2e"
        ).pack(pady=(10, 5))

        tk.Label(
            frame, text="Enter your Google Gemini API Key to start",
            font=("Arial", 12), fg="#cdd6f4", bg="#1e1e2e"
        ).pack(pady=(0, 20))

        self.api_entry = tk.Entry(frame, width=48, font=("Consolas", 11), show="*")
        self.api_entry.pack(pady=10, ipady=6)

        # TODO (للزميل المسؤول عن الواجهة):
        # 1. نقل الواجهة بالكامل إلى Flask (HTML/CSS/JS) لدعم اللغة العربية (RTL) بشكل طبيعي وتصميم حديث.
        # 2. حفظ الـ API Key في ملف محلي على الجهاز أول مرة المستخدم يدخله،
        #    عشان لما يفتح البرنامج بعد كده يدخل على لوحة التحكم علطول من غير ما يكتبه كل مرة.

        tk.Button(
            frame, text="Connect & Launch Dashboard",
            font=("Arial", 11, "bold"), bg="#a6e3a1", fg="#11111b",
            padx=20, pady=8, cursor="hand2",
            command=self._on_connect_api
        ).pack(pady=15)

    def _on_connect_api(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please enter your Gemini API Key first.")
            return

        try:
            self.ai_engine = AIEngine(api_key=api_key)
            self._build_dashboard_page()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to Gemini:\n{e}")

    # ------------------------------------------------------------------
    # الصفحة الثانية: لوحة التحكم الرئيسية
    # ------------------------------------------------------------------
    def _build_dashboard_page(self):
        self._clear_window()

        container = tk.Frame(self.root, bg="#1e1e2e", padx=20, pady=15)
        container.pack(expand=True, fill="both")

        # زرار بدء وإيقاف التسجيل الصوتي
        self.record_btn = tk.Button(
            container, text="🎤 Start Recording",
            font=("Arial", 12, "bold"), bg="#89b4fa", fg="#11111b",
            padx=20, pady=10, cursor="hand2",
            command=self._toggle_recording
        )
        self.record_btn.pack(fill="x", pady=(0, 12))

        self.status_label = tk.Label(
            container, text="Ready to listen...", font=("Arial", 10),
            fg="#a6adc8", bg="#1e1e2e"
        )
        self.status_label.pack(anchor="w", pady=(0, 10))

        # مربع عرض الكلام اللي المستخدم قاله
        tk.Label(container, text="Transcript:", fg="#cdd6f4", bg="#1e1e2e").pack(anchor="w")
        self.transcript_box = tk.Text(container, height=2, font=("Arial", 11), bg="#313244", fg="#ffffff")
        self.transcript_box.pack(fill="x", pady=(2, 10))

        # مربع عرض الأمر المقترح / نية المستخدم
        # TODO (للزميل المسؤول عن الواجهة):
        # 1. بدل ما نعرض كود الـ Bash للمستخدم العادي، نعرضله نية العملية (INTENT) بكلام بشري بسيط يفهمه.
        # 2. نخفي كود الـ Bash خالص عن المستخدم العادي، ومنظهروش إلا لو متغير `config.DEV_MODE` معمول True.
        # 3. لو الرد راجع بـ `status == "CONFLICT"` (يعني فيه ملف موجود بنفس الاسم)، نعرض رسالة تنبيه تطلب من المستخدم يختار اسم تاني.
        tk.Label(container, text="Proposed Action / Command:", fg="#cdd6f4", bg="#1e1e2e").pack(anchor="w")
        self.command_box = tk.Text(container, height=2, font=("Consolas", 11), bg="#313244", fg="#a6e3a1")
        self.command_box.pack(fill="x", pady=(2, 10))

        # أزرار التنفيذ والمسح
        btn_frame = tk.Frame(container, bg="#1e1e2e")
        btn_frame.pack(fill="x", pady=5)

        tk.Button(
            btn_frame, text="✅ Execute",
            font=("Arial", 11, "bold"), bg="#a6e3a1", fg="#11111b",
            padx=15, pady=6, cursor="hand2",
            command=self._execute_current_command
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_frame, text="🗑️ Clear",
            font=("Arial", 11), bg="#f38ba8", fg="#11111b",
            padx=15, pady=6, cursor="hand2",
            command=self._clear_outputs
        ).pack(side="left")

        # مربع عرض نتيجة تنفيذ الأمر
        tk.Label(container, text="Execution Output:", fg="#cdd6f4", bg="#1e1e2e").pack(anchor="w", pady=(10, 2))
        self.output_area = scrolledtext.ScrolledText(
            container, height=8, font=("Consolas", 10), bg="#181825", fg="#cdd6f4"
        )
        self.output_area.pack(expand=True, fill="both")

    def _toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.config(text="⏹️ Stop & Process", bg="#f38ba8")
            self.status_label.config(text="Recording... Speak now", fg="#f9e2af")
            self.recorder.start()
        else:
            self.is_recording = False
            self.record_btn.config(text="🎤 Start Recording", bg="#89b4fa")
            self.status_label.config(text="Processing audio with Gemini...", fg="#89b4fa")
            audio_bytes = self.recorder.stop()
            threading.Thread(target=self._process_audio_thread, args=(audio_bytes,), daemon=True).start()

    def _process_audio_thread(self, audio_bytes: bytes):
        try:
            file_map = context_scanner.get_environment_map()
            result = self.ai_engine.process_audio(audio_bytes, file_context=file_map)
            self.root.after(0, self._update_ui_with_result, result)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.status_label.config(text="An error occurred during processing.", fg="#f38ba8"))

    def _update_ui_with_result(self, result: dict):
        self.transcript_box.delete("1.0", tk.END)
        self.transcript_box.insert(tk.END, result.get("transcript", ""))

        self.current_command = result.get("command", "")
        self.command_box.delete("1.0", tk.END)
        self.command_box.insert(tk.END, self.current_command)

        model_used = result.get("model_used", "")
        self.status_label.config(text=f"Processed successfully (Model: {model_used})", fg="#a6e3a1")

    def _execute_current_command(self):
        cmd = self.command_box.get("1.0", tk.END).strip()
        if not cmd:
            messagebox.showwarning("Warning", "No command to execute.")
            return

        # TODO (للزميل المسؤول عن الواجهة والتنفيذ):
        # قبل التنفيذ، نتأكد عن طريق `executor.is_dangerous_command(cmd)` لو الأمر خطير (زي الحذف النهائي)،
        # ولو خطير نطلع رسالة تحذير واضحة للمستخدم للتأكيد مرتين قبل ما ينفذ.

        res = executor.run_command(cmd)
        self.output_area.insert(tk.END, f"$ {cmd}\n{res['output']}\n{'-'*40}\n")
        self.output_area.see(tk.END)

    def _clear_outputs(self):
        self.transcript_box.delete("1.0", tk.END)
        self.command_box.delete("1.0", tk.END)
        self.output_area.delete("1.0", tk.END)
        self.current_command = ""

    def _clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
