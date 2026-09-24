import requests
import sqlite3
from datetime import datetime
import sys




# =========================================================
# SETTINGS
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "ai-assistant"
DB_PATH = "C:/AI_Assistant/memory.db"

conversation_history = []


# =========================================================
# UTF-8 / RTL
# =========================================================

try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def print_rtl(text=""):
    print(text)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # Create table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'عمومی',
            created_at TEXT NOT NULL
        )
    """)

    # Check existing columns
    cursor.execute("PRAGMA table_info(memories)")
    columns = [row[1] for row in cursor.fetchall()]

    # Migration for old database
    if "category" not in columns:
        cursor.execute("""
            ALTER TABLE memories
            ADD COLUMN category TEXT DEFAULT 'عمومی'
        """)

    conn.commit()
    conn.close()


def save_memory(content, category="عمومی"):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memories
        (content, category, created_at)
        VALUES (?, ?, ?)
        """,
        (
            content,
            category,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_memories():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, content, category
        FROM memories
        ORDER BY id ASC
    """)

    result = cursor.fetchall()

    conn.close()

    return result


def search_memories(text):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, content, category
        FROM memories
        WHERE content LIKE ?
        ORDER BY id ASC
        """,
        (f"%{text}%",)
    )

    result = cursor.fetchall()

    conn.close()

    return result


def delete_memory(memory_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM memories WHERE id = ?",
        (memory_id,)
    )

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


def clear_memories():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM memories")

    conn.commit()
    conn.close()


# =========================================================
# MEMORY DISPLAY
# =========================================================

def show_memories():

    memories = get_memories()

    if not memories:
        print_rtl("\nدستیار: حافظه دائمی من خالی است.\n")
        return

    print_rtl("\n========== حافظه دائمی ==========\n")

    for memory_id, content, category in memories:

        print_rtl(
            f"{memory_id}. [{category}] {content}"
        )

    print_rtl("\n==================================\n")


# =========================================================
# INTERNAL MEMORY COMMANDS
# =========================================================

def handle_memory_command(user_input):

    # -----------------------------------------------------
    # یادداشت کن
    # -----------------------------------------------------

    if user_input.startswith("یادداشت کن"):

        memory = user_input.replace(
            "یادداشت کن",
            "",
            1
        ).strip()

        if memory:

            save_memory(memory)

            print_rtl(
                "\nدستیار: این مورد را در حافظه دائمی ذخیره کردم.\n"
            )

        else:

            print_rtl(
                "\nدستیار: بعد از «یادداشت کن» "
                "متنی را که می‌خواهید ذخیره شود بنویسید.\n"
            )

        return True


    # -----------------------------------------------------
    # ذخیره کن
    # -----------------------------------------------------

    if user_input.startswith("ذخیره کن"):

        memory = user_input.replace(
            "ذخیره کن",
            "",
            1
        ).strip()

        if memory:

            save_memory(memory)

            print_rtl(
                "\nدستیار: ذخیره شد.\n"
            )

        else:

            print_rtl(
                "\nدستیار: متن موردنظر برای ذخیره را وارد کنید.\n"
            )

        return True


    # -----------------------------------------------------
    # نمایش حافظه
    # -----------------------------------------------------

    if user_input in [
        "حافظه",
        "حافظه من",
        "حافظه‌ها",
        "چه چیزهایی از من یادت هست؟",
        "چه چیزهایی یادت هست؟",
        "حافظه من را نشان بده"
    ]:

        show_memories()

        return True


    # -----------------------------------------------------
    # جستجوی حافظه
    # -----------------------------------------------------

    if user_input.startswith("جستجوی حافظه"):

        text = user_input.replace(
            "جستجوی حافظه",
            "",
            1
        ).strip()

        if not text:

            print_rtl(
                "\nدستیار: عبارت موردنظر را برای جستجو وارد کنید.\n"
            )

            return True

        results = search_memories(text)

        if not results:

            print_rtl(
                "\nدستیار: موردی پیدا نکردم.\n"
            )

        else:

            print_rtl("\nنتایج جستجو:\n")

            for memory_id, content, category in results:

                print_rtl(
                    f"{memory_id}. [{category}] {content}"
                )

            print()


        return True


    # -----------------------------------------------------
    # حذف حافظه
    # -----------------------------------------------------

    if user_input.startswith("حذف حافظه"):

        value = user_input.replace(
            "حذف حافظه",
            "",
            1
        ).strip()

        try:

            memory_id = int(value)

            if delete_memory(memory_id):

                print_rtl(
                    "\nدستیار: حافظه موردنظر حذف شد.\n"
                )

            else:

                print_rtl(
                    "\nدستیار: چنین شماره‌ای در حافظه وجود ندارد.\n"
                )

        except ValueError:

            print_rtl(
                "\nدستیار: شماره حافظه را وارد کنید. "
                "مثلاً: حذف حافظه 3\n"
            )

        return True


    # -----------------------------------------------------
    # پاک کردن کل حافظه
    # -----------------------------------------------------

    if user_input == "پاک کردن همه حافظه":

        clear_memories()

        print_rtl(
            "\nدستیار: تمام حافظه دائمی پاک شد.\n"
        )

        return True


    return False


# =========================================================
# ASK QWEN
# =========================================================

def ask_ai(user_input):

    conversation_history.append(
        f"کاربر: {user_input}"
    )

    conversation = "\n".join(
        conversation_history[-20:]
    )

    memories = get_memories()

    if memories:

        permanent_memory = "\n".join(
            f"- [{category}] {content}"
            for _, content, category in memories
        )

    else:

        permanent_memory = "حافظه دائمی خالی است."


    prompt = f"""
تو یک دستیار هوش مصنوعی محلی و فارسی‌زبان هستی.

قواعد:

- فارسی طبیعی و روان صحبت کن.
- پاسخ‌ها را واضح و کاربردی بده.
- اطلاعات موجود در حافظه دائمی را در صورت مرتبط بودن در نظر بگیر.
- اطلاعاتی که در حافظه نیستند را جعل نکن.
- اگر کاربر درباره خودش اطلاعات جدیدی می‌دهد، در صورت اهمیت
  می‌توانی پیشنهاد ذخیره آن را بدهی.
- حافظه دائمی زیر اطلاعاتی است که کاربر قبلاً برای ذخیره نگه داشته است.

حافظه دائمی:

{permanent_memory}

تاریخچه مکالمه:

{conversation}

کاربر:

{user_input}

دستیار:
"""


    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }


    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    data = response.json()

    answer = data.get(
        "response",
        ""
    ).strip()


    conversation_history.append(
        f"دستیار: {answer}"
    )

    return answer


# =========================================================
# MAIN
# =========================================================

init_database()


print("=" * 50)
print_rtl("        دستیار هوش مصنوعی محلی")
print("=" * 50)

print_rtl("مدل Qwen آماده است.")
print_rtl("حافظه دائمی فعال است.")

print_rtl("""
فرمان‌های حافظه:

  یادداشت کن ...
  حافظه
  جستجوی حافظه ...
  حذف حافظه شماره
  پاک کردن همه حافظه
  exit
""")


while True:

    try:

        user_input = input("شما: ").strip()

        if not user_input:
            continue


        # خروج

        if user_input.lower() == "exit":

            print_rtl("دستیار خاموش شد.")

            break


        # فرمان‌های داخلی حافظه

        if handle_memory_command(user_input):

            continue


        # سؤال عادی

        answer = ask_ai(user_input)

        print_rtl(
            "\nدستیار: " + answer
        )

        print()


    except requests.exceptions.ConnectionError:

        print_rtl(
            "\nخطا: Ollama در حال اجرا نیست."
        )

        print_rtl(
            "ابتدا Ollama را اجرا کنید.\n"
        )


    except requests.exceptions.Timeout:

        print_rtl(
            "\nخطا: زمان پاسخ‌گویی Ollama تمام شد.\n"
        )


    except Exception as e:

        print_rtl(
            f"\nخطا: {e}\n"
        )