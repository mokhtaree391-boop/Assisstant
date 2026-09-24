import os
import base64
import requests
from datetime import datetime

# ---------- تنظیمات مدل تصویری (Vision) ----------
# این مدل جدا از مدل اصلی ایجنت (qwen2.5:7b) است و فقط برای «دیدن» اسکرین‌شات صفحه استفاده می‌شود.
# قبل از استفاده باید نصبش کنید:  ollama pull qwen2.5vl:7b
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:7b")

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")


def _describe_screenshot(image_path: str, question: str = None) -> str:
    """
    اسکرین‌شات را به یک مدل vision در Ollama می‌دهد و توضیح متنی از آنچه
    در صفحه دیده می‌شود (چیدمان، دکمه‌ها، فرم‌ها، متن‌های مهم و ...) برمی‌گرداند.
    """
    try:
        with open(image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"خطا در خواندن فایل اسکرین‌شات: {e}"

    prompt = question or (
        "این تصویر یک اسکرین‌شات از صفحه مرورگر است. آنچه در صفحه می‌بینی را دقیق و "
        "خلاصه توصیف کن: عنوان/موضوع صفحه، بخش‌های اصلی، دکمه‌ها و فیلدهای فرم، "
        "پیام‌های خطا یا هشدار (در صورت وجود)، و هر چیز مهم دیگری که کاربر باید بداند. "
        "پاسخ را به فارسی و به‌صورت خلاصه بنویس."
    )

    payload = {
        "model": VISION_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64_image],
            }
        ],
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip() or "مدل تصویری پاسخ خالی برگرداند."
    except requests.exceptions.ConnectionError:
        return (
            "خطا: اتصال به Ollama برقرار نشد. مطمئن شوید Ollama در حال اجراست "
            "(دستور: ollama serve)."
        )
    except requests.exceptions.HTTPError as e:
        return (
            f"خطا در فراخوانی مدل تصویری «{VISION_MODEL}». احتمالاً این مدل نصب نیست.\n"
            f"برای نصب در ترمینال بزنید: ollama pull {VISION_MODEL}\n"
            f"جزئیات فنی: {e}"
        )
    except Exception as e:
        return f"خطا در تحلیل تصویری صفحه: {e}"


def open_browser(url: str = "https://www.google.com", see_page: bool = True) -> str:
    """
    یک صفحه مرورگر کروم واقعی روی سیستم باز می‌کند، به آدرس مورد نظر می‌رود،
    از صفحه اسکرین‌شات می‌گیرد و آن را به یک مدل تصویری (vision) می‌دهد تا ایجنت
    بتواند بفهمد صفحه از نظر بصری چه شکلی است (نه فقط متن خام آن)، سپس محتوای
    متنی صفحه را هم استخراج می‌کند. مرورگر باز می‌ماند تا کاربر خودش آن را ببندد.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (
            "خطا: کتابخانه Playwright نصب نیست. در ترمینال بزنید:\n"
            "pip install playwright\n"
            "playwright install chromium"
        )

    try:
        with sync_playwright() as p:
            # باز کردن مرورگر به صورت کاملاً نمایشی و تمام‌صفحه
            browser = p.chromium.launch(channel="chrome", headless=False, args=["--start-maximized"])
            page = browser.new_page(no_viewport=True)
            page.goto(url)
            print(f"صفحه {url} با موفقیت باز شد.")

            # انتظار برای لود کامل محتوای صفحه
            page.wait_for_load_state("domcontentloaded", timeout=15000)

            # استخراج محتوای متنی بدنه صفحه
            page_content = page.inner_text("body")
            trimmed_content = page_content[:1500] + "..." if len(page_content) > 1500 else page_content

            # ---------- گرفتن اسکرین‌شات و تحلیل بصری صفحه ----------
            vision_description = None
            if see_page:
                try:
                    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(SCREENSHOTS_DIR, f"page_{timestamp}.png")
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"اسکرین‌شات ذخیره شد: {screenshot_path}")
                    vision_description = _describe_screenshot(screenshot_path)
                except Exception as e:
                    vision_description = f"خطا در گرفتن اسکرین‌شات: {e}"

            print("مرورگر باز است. برای ادامه، پنجره را به صورت دستی ببندید...")

            # صبر نامحدود تا کاربر خودش پنجره مرورگر را ببندد (timeout=0 یعنی بدون محدودیت زمانی)
            try:
                page.wait_for_event("close", timeout=0)
            except Exception:
                # اگر کاربر کل پنجره مرورگر (نه فقط تب) را ببندد، ممکن است رویداد close
                # به همین شکل fire نشود؛ در این صورت منتظر قطع اتصال کامل مرورگر می‌مانیم
                try:
                    browser.wait_for_event("disconnected", timeout=0)
                except Exception:
                    pass

            # اطمینان از بسته شدن کامل (اگر کاربر قبلاً بسته باشد، این خط خطا نمی‌دهد)
            try:
                browser.close()
            except Exception:
                pass

            # ---------- ساخت خروجی نهایی ----------
            result = f"موفق! صفحه {url} باز و بررسی شد.\n"
            if see_page and vision_description:
                result += f"\n--- توضیح تصویری صفحه (آنچه دیده می‌شود) ---\n{vision_description}\n"
            result += f"\n--- متن استخراج‌شده از صفحه ---\n{trimmed_content}"
            return result

    except Exception as e:
        return f"خطا در باز کردن یا خواندن مرورگر: {str(e)}"


if __name__ == "__main__":
    print(open_browser("https://shafadoc.ir/Account"))
