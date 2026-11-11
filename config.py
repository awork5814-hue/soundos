import os
import json
import time

# ==========================================
# 1. إعدادات الصوت الأساسية (Audio Settings)
# ==========================================
SAMPLE_RATE = 16000
CHANNELS = 1

# ==========================================
# 2. إعدادات الموديلات والتحديث التلقائي (كل 10 أيام)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_CACHE_FILE = os.path.join(BASE_DIR, "models_cache.json")
CACHE_EXPIRY_SECONDS = 10 * 24 * 60 * 60  # 10 أيام بالثواني

DEFAULT_PREFERRED_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash"
]

DEPRECATED_MODEL_TAGS = ["1.0", "1.5", "2.5"]

def save_discovered_models(models_list):
    """حفظ قائمة الموديلات وتاريخ التحديث في ملف الكاش"""
    data = {
        "last_updated": time.time(),
        "models": models_list
    }
    try:
        with open(MODELS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Config Warning]: {e}")

def load_cached_models():
    """قراءة الموديلات المحفوظة إذا لم يمر عليها أكثر من 10 أيام"""
    if not os.path.exists(MODELS_CACHE_FILE):
        return None
    try:
        with open(MODELS_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("last_updated", 0) > CACHE_EXPIRY_SECONDS:
            return None
        return data.get("models") or None
    except Exception:
        return None

# ==========================================
# 3. إعدادات نطاق فحص الملفات (للتطوير في context_scanner.py)
# ==========================================
HOME_DIR = os.path.expanduser("~")

# المجلدات المسموح للنظام برؤية أسماء ومسارات ملفاتها فقط (يمكن للفريق تعديلها)
ALLOWED_DIRS = [
    os.path.join(HOME_DIR, "Desktop"),
    os.path.join(HOME_DIR, "Documents"),
    os.path.join(HOME_DIR, "Downloads")
]

# أقصى عمق للدخول داخل الفولدرات الفرعية
MAX_SCAN_DEPTH = 2

# ==========================================
# 4. إعدادات الأمان والحذف (للتطوير في executor.py)
# ==========================================
# أمر الحذف الافتراضي الآمن (ينقل لسلة المهملات)
SAFE_DELETE_COMMAND = "gio trash"

# كلمات/أنماط خطيرة تتطلب تأكيداً مزدوجاً أو طلباً صريحاً بالحذف النهائي
DANGEROUS_PATTERNS = ["rm -rf", "rm -r", "mkfs", "dd if=", ":(){", "sudo rm"]

# ==========================================
# 5. إعدادات الواجهة والألوان (للتطوير في gui.py)
# ==========================================
# وضع المطورين: True لعرض مربع كود الـ Bash، و False لإخفائه والاكتفاء بتأكيد النية البشرية
DEV_MODE = True

COLORS = {
    "bg_main": "#1e1e2e",
    "bg_card": "#181825",
    "bg_input": "#313244",
    "bg_log": "#11111b",
    "text_primary": "#cdd6f4",
    "text_muted": "#a6adc8",
    "accent_blue": "#89b4fa",
    "accent_green": "#a6e3a1",
    "accent_yellow": "#f9e2af",
    "accent_peach": "#fab387",
    "accent_red": "#f38ba8",
    "text_dark": "#11111b"
}
