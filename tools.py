# -*- coding: utf-8 -*-
import os, requests, urllib.parse, paramiko
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def web_search(query: str) -> str:
    """Search Google and DuckDuckGo with fallback"""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(f"Title: {r.get('title')}\nLink: {r.get('href')}\nSnippet: {r.get('body')}")
        if results:
            return '\n---\n'.join(results)
    except Exception:
        pass
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
        resp = requests.post(url, data={'q': query}, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', class_='result__snippet')[:3]:
            results.append(f"Snippet: {a.get_text(strip=True)}")
        if results:
            return '\n---\n'.join(results)
    except Exception as e:
        return f'خطا در جستجو: {str(e)}'
    return 'نتیجهای یافت نشد یا دسترسی اینترنت با اختلال مواجه شد.'


def read_file(file_path: str) -> str:
    try:
        if not os.path.exists(file_path):
            return f'خطا: فایل {file_path} پیدا نشد.'
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'خطا در خواندن: {str(e)}'


def write_file(file_path: str, content: str) -> str:
    try:
        if os.path.dirname(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f'فایل {file_path} با موفقیت ذخیره شد.'
    except Exception as e:
        return f'خطا در نوشتن: {str(e)}'


def ssh_exec(hostname, username, password, command, port=22):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, timeout=10)
        stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        client.close()
        return out if out else err
    except Exception as e:
        return f'SSH Error: {str(e)}'


def open_browser(url: str = "https://www.google.com", see_page: bool = True) -> str:
    """
    ابزار مرورگر — بهصورت تنبل (lazy) بارگذاری میشود تا در صورت نبودن
    کتابخانه Playwright کل سرور از کار نیفتد فقط همین ابزار خطا میدهد.
    see_page=True یعنی از صفحه اسکرینشات گرفته و با یک مدل تصویری تحلیل شود.
    """
    try:
        from app.browser_tool import open_browser as _open_browser
        return _open_browser(url, see_page=see_page)
    except ImportError as e:
        return (
            "خطا: کتابخانه مرورگر (Playwright) نصب نیست.\n"
            "برای نصب در ترمینال بزنید:\n"
            "pip install playwright\n"
            "playwright install chromium\n"
            f"جزئیات فنی: {e}"
        )
    except Exception as e:
        return f"خطا در اجرای ابزار مرورگر: {e}"
