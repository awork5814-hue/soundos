import subprocess
import config

def sanitize_command(command: str) -> str:
    """
    تعديل أوامر الحذف العادية لاستخدام سلة المهملات بأمان.
    
    TODO (للزميل المسؤول عن executor):
    1. استيراد `config.SAFE_DELETE_COMMAND` (الذي يساوي 'gio trash').
    2. فحص الأمر: إذا كان يحتوي على أمر حذف عادي (`rm ` بدون طلب حذف نهائي صريح)،
       استبدله بـ `gio trash` لنقل الملف إلى سلة المهملات بأمان.
    """
    # Placeholder: يمرر الأمر كما هو حالياً
    return command

def is_dangerous_command(command: str) -> bool:
    """
    فحص ما إذا كان الأمر يمثل خطورة أو يتطلب تأكيداً مزدوجاً.
    
    TODO (للزميل المسؤول عن executor):
    1. استيراد `config.DANGEROUS_PATTERNS`.
    2. التحقق مما إذا كان الأمر يحتوي على أنماط خطيرة مثل `rm -rf` أو `mkfs` أو `dd`.
    3. إرجاع True إذا كان خطيراً ليتم طلب تأكيد مزدوج من المستخدم.
    """
    # Placeholder: يرجع False حالياً
    return False

def run_command(command: str) -> dict:
    """تنفيذ أمر الـ Bash في الخلفية وإرجاع النتيجة"""
    if not command or not command.strip():
        return {"success": False, "output": "لا يوجد أمر لتنفيذه."}

    safe_cmd = sanitize_command(command)

    try:
        completed = subprocess.run(
            safe_cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=30
        )
        output = completed.stdout.strip() or completed.stderr.strip() or "تم التنفيذ بنجاح."
        return {
            "success": completed.returncode == 0,
            "output": output
        }
    except Exception as e:
        return {"success": False, "output": f"خطأ أثناء التنفيذ: {str(e)}"}
