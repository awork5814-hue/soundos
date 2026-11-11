import os
import config

def get_environment_map() -> str:
    """
    فحص أسماء ومسارات الملفات في النطاق المسموح فقط (Metadata Only).
    
    TODO (للزميل المسؤول عن context_scanner):
    1. استيراد واستخدام `config.ALLOWED_DIRS` و `config.MAX_SCAN_DEPTH`.
    2. المرور على المجلدات المسموحة وتجميع أسماء ومسارات الملفات والفولدرات فقط
       دون فتح أي ملف أو قراءة محتواه (لحماية الخصوصية).
    3. إرجاع النتيجة كنص منسق لتمريره إلى `ai_engine.py`.
    """
    allowed_dirs = getattr(config, "ALLOWED_DIRS", [])
    max_depth = getattr(config, "MAX_SCAN_DEPTH", 2)

    # Placeholder: يرجع نص فاضي حالياً حتى يتم تنفيذ منطق الفحص
    return ""
