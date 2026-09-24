# -*- coding: utf-8 -*-
import os
import shutil
import sys

APP_DIR = r"C:\AI_Assistant\app"
GUI = os.path.join(APP_DIR, "gui.py")
BACKUP_DIR = os.path.join(r"C:\AI_Assistant", "backups")

def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # 1) حذف پرینت‌های دیباگ از gui.py
    if os.path.exists(GUI):
        with open(GUI, "r", encoding="utf-8") as f:
            content = f.read()

        old = '''        print("=" * 50)
        print("DEBUG >> پیام دریافتی از کاربر:")
        print(repr(user))
        print("DEBUG >> ابزار تشخیص داده شده:", tool)
        print("DEBUG >> آرگومان‌ها:", args)
        print("=" * 50)

        if tool:

            result = execute_tool(tool,args)

            print("DEBUG >> طول نتیجه ابزار (کاراکتر):", len(result) if result else 0)
            print("DEBUG >> 300 کاراکتر ابتدای نتیجه:")
            print(result[:300] if result else "(خالی است!)")
            print("=" * 50)'''

        new = '''        if tool:

            result = execute_tool(tool, args)'''

        if old in content:
            content = content.replace(old, new)
            with open(GUI, "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ پرینت‌های دیباگ از gui.py حذف شدند.")
        else:
            print("⚠️ بلوک دیباگ دقیقاً پیدا نشد (اشکالی ندارد، رد می‌شویم).")
    else:
        print("❌ gui.py پیدا نشد.")

    # 2) انتقال فایل‌های بک‌آپ/اضافی به پوشه backups
    move_list = [
        "gui_backup_before_chat_fix.py",
        "gui_backup_before_fix.py",
        "gui_safe_backup.py",
        "gui_before_autofix.py",
        "gui_before_debug.py",
        "main_backup.py",
    ]

    for fname in move_list:
        src = os.path.join(APP_DIR, fname)
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, fname)
            shutil.move(src, dst)
            print(f"📦 منتقل شد: {fname} -> backups/")

    print("\n🎉 تمیزکاری تمام شد.")

if __name__ == "__main__":
    main()
