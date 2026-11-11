import os
import json
import time
from google import genai
from google.genai import types
import config

class AIEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        self.models = self._load_models()

    def _load_models(self):
        """
        الأولوية:
        1. قراءة الكاش لو صالح، أو السحب من config.DEFAULT_PREFERRED_MODELS مباشرة.
        2. في حالة عدم وجودهم في config، يتم اكتشافهم من الـ API وحفظهم.
        """
        cache_file = getattr(config, "MODELS_CACHE_FILE", "")
        expiry = getattr(config, "CACHE_EXPIRY_SECONDS", 864000)
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() - data.get("last_updated", 0) < expiry and data.get("models"):
                    return data["models"]
            except Exception:
                pass

        preferred = getattr(config, "DEFAULT_PREFERRED_MODELS", [])
        if preferred:
            return preferred

        return self._discover_and_save_models()

    def _discover_and_save_models(self):
        """اكتشاف الموديلات من API وحفظها في الكاش عبر دالة config"""
        discovered = []
        deprecated = getattr(config, "DEPRECATED_MODEL_TAGS", [])
        try:
            for m in self.client.models.list():
                name = getattr(m, "name", "").replace("models/", "")
                if "gemini" in name and ("flash" in name or "pro" in name):
                    if not any(tag in name for tag in deprecated):
                        discovered.append(name)
            if discovered and hasattr(config, "save_discovered_models"):
                config.save_discovered_models(discovered)
        except Exception:
            pass
        return discovered or ["gemini-2.0-flash"]

    def _build_system_prompt(self, file_context: str = "") -> str:
        """
        بناء الـ System Prompt الموجه للموديل.
        TODO (للزميل المسؤول عن ai_engine):
        1. دمج متغير `file_context` القادم من `context_scanner.py` داخل الـ Prompt ليفهم الموديل مسارات الملفات الحقيقية.
        2. تعديل صيغة المخرجات لتشمل:
           - STATUS: (READY أو CONFLICT).
           - TRANSCRIPT: ما قاله المستخدم.
           - INTENT: وصف بشري واضح وبسيط للعملية (ليظهر للمستخدم بدلاً من كود Bash).
           - COMMAND: أمر الـ Bash التنفيذي.
        3. منع الكتابة فوق الملفات الموجودة (No Auto-Overwrite): إذا طلب المستخدم إنشاء/كتابة ملف موجود مسبقاً في `file_context`، يتم إرجاع `STATUS: CONFLICT` وإبلاغ المستخدم بوضوح أن الملف موجود بالفعل بنفس الاسم (على غرار نظام ويندوز) والطلب منه تحديد اسم جديد للملف.
        4. التمييز في الـ Prompt بين الحذف العادي (`gio trash`) والحذف النهائي (`rm -rf`) بناءً على صراحة طلب المستخدم.
        """
        base_prompt = """
        You are SoundOS, an intelligent Ubuntu Linux assistant.
        Listen to the user's audio command (in Egyptian Arabic or English) and translate it into a safe Linux Bash command.
        
        Output strictly in the following format:
        TRANSCRIPT: <what the user said>
        INTENT: <TODO: human-readable explanation in the user's language>
        COMMAND: <valid ubuntu bash command>
        """
        return base_prompt.strip()

    def process_audio(self, audio_bytes: bytes, file_context: str = "") -> dict:
        """إرسال الصوت المسجل في الذاكرة (RAM) إلى Gemini مع نظام بدائل تلقائي"""
        prompt = self._build_system_prompt(file_context)
        last_error = None

        for model_name in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type="audio/wav"
                        )
                    ]
                )
                return self._parse_response(response.text, model_name)

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"فشلت جميع الموديلات المتاحة. آخر خطأ: {last_error}")

    def _parse_response(self, raw_text: str, used_model: str) -> dict:
        """
        تحليل رد Gemini واستخراج الحالة، النص المفرغ، النية، والأمر.
        TODO (للزميل المسؤول عن ai_engine):
        - استخراج حقل STATUS (للتعامل مع حالات CONFLICT) وحقل INTENT وتمريرهم للواجهة.
        """
        result = {
            "status": "READY",
            "transcript": "",
            "intent": "تنفيذ الأمر المطلوب",
            "command": "",
            "model_used": used_model
        }

        for line in raw_text.strip().splitlines():
            if line.startswith("STATUS:"):
                result["status"] = line.replace("STATUS:", "").strip()
            elif line.startswith("TRANSCRIPT:"):
                result["transcript"] = line.replace("TRANSCRIPT:", "").strip()
            elif line.startswith("INTENT:"):
                result["intent"] = line.replace("INTENT:", "").strip()
            elif line.startswith("COMMAND:"):
                cmd = line.replace("COMMAND:", "").strip()
                cmd = cmd.replace("```bash", "").replace("```", "").strip()
                result["command"] = cmd

        return result
