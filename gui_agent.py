import os
import json
import sqlite3
import requests
from flask import Flask, request, jsonify, render_template_string
from app.tools import web_search, read_file, write_file, ssh_exec

app = Flask(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:7b"
DB_PATH = "C:/AI_Assistant/memory.db"
MAX_AGENT_STEPS = 6   # جلوگیری از حلقه بی‌نهایت


# ---------- MEMORY ----------

def get_memory():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, content, category FROM memories ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "حافظه خالی است."
    return "\n".join(f"{r[0]} [{r[2]}] {r[1]}" for r in rows)


def save_memory(text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO memories (content, category) VALUES (?, ?)", (text, "عمومی"))
    conn.commit()
    conn.close()


# ---------- TOOL SCHEMAS (چیزی که به مدل معرفی می‌شود) ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "خواندن محتوای کامل یک فایل از روی سیستم، همراه با تعداد خطوط و لیست توابع/کلاس‌های آن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "مسیر کامل فایل، مثل C:\\AI_Assistant\\app\\main.py"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "نوشتن یا جایگزینی محتوای یک فایل روی سیستم.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "جستجو در اینترنت برای اطلاعات به‌روز.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_exec",
            "description": "اجرای یک دستور روی سرور راه دور از طریق SSH.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "command": {"type": "string"},
                    "port": {"type": "integer"}
                },
                "required": ["hostname", "username", "password", "command"]
            }
        }
    }
]


# ---------- TOOL EXECUTION ----------

def execute_tool(name, args):
    try:
        if name == "read_file":
            path = args["file_path"]
            content = read_file(path)

            if content.startswith("خطا"):
                return content

            lines = content.splitlines()
            functions, classes = [], []
            for line in lines:
                s = line.strip()
                if s.startswith("def "):
                    functions.append(s.split("(")[0].replace("def ", ""))
                if s.startswith("class "):
                    classes.append(s.split(":")[0].replace("class ", ""))

            return (
                f"FILE_PATH: {path}\n"
                f"LINE_COUNT: {len(lines)}\n"
                f"FUNCTIONS: {', '.join(functions) if functions else 'ندارد'}\n"
                f"CLASSES: {', '.join(classes) if classes else 'ندارد'}\n\n"
                f"FILE_CONTENT:\n{content}"
            )

        elif name == "web_search":
            return web_search(args["query"])

        elif name == "write_file":
            return write_file(args["file_path"], args["content"])

        elif name == "ssh_exec":
            return ssh_exec(
                args["hostname"], args["username"], args["password"],
                args["command"], args.get("port", 22)
            )

        else:
            return f"ابزار ناشناخته: {name}"

    except Exception as e:
        return f"خطا در اجرای ابزار {name}: {e}"


# ---------- SYSTEM ----------

SYSTEM = """
تو یک دستیار هوشمند فارسی هستی که به ابزارها دسترسی داری.

قوانین مهم:
- اگر برای پاسخ به سوال کاربر نیاز به خواندن فایل، جستجوی وب، نوشتن فایل یا اجرای دستور SSH داری،
  حتماً از ابزار مربوطه استفاده کن. هرگز محتوای فایل یا نتیجه جستجو را حدس نزن.
- بعد از دریافت نتیجه‌ی یک ابزار، فقط بر اساس همان نتیجه‌ی واقعی پاسخ بده.
- اگر LINE_COUNT در نتیجه‌ی read_file وجود دارد، همان عدد دقیق را گزارش کن.
- وقتی اطلاعات کافی برای پاسخ نهایی داری، دیگر ابزار صدا نزن و مستقیم پاسخ نهایی فارسی بده.
"""


# ---------- OLLAMA CALL ----------

def call_ollama(messages, use_tools=True):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 16384,
            "num_predict": 1024
        }
    }
    if use_tools:
        payload["tools"] = TOOLS

    r = requests.post(OLLAMA_URL, json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["message"]


# ---------- AGENT LOOP ----------

def run_agent(user_message):
    messages = [
        {"role": "system", "content": SYSTEM + "\n\nحافظه دائمی:\n" + get_memory()},
        {"role": "user", "content": user_message}
    ]

    steps_log = []

    for step in range(MAX_AGENT_STEPS):
        msg = call_ollama(messages)

        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            # مدل تصمیم گرفته پاسخ نهایی بدهد
            return msg.get("content", ""), steps_log

        # مدل حداقل یک ابزار خواسته -> پیام assistant را (با tool_calls) اضافه کن
        messages.append(msg)

        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]

            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}

            print(f"[AGENT STEP {step+1}] tool={fn_name} args={fn_args}")

            result = execute_tool(fn_name, fn_args)

            steps_log.append({"tool": fn_name, "args": fn_args, "result_len": len(result)})

            # نتیجه ابزار را به گفتگو اضافه کن تا مدل در گام بعد ببیند
            messages.append({
                "role": "tool",
                "content": result
            })

    return "متاسفانه پس از چند مرحله نتوانستم به پاسخ نهایی برسم.", steps_log


# ---------- HTML (همان قبلی) ----------

HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>دستیار هوش مصنوعی - Agent</title>
<style>
body{margin:0;background:#f1f7f3;font-family:Tahoma,Arial,sans-serif;}
header{background:#dcefe5;padding:18px;text-align:center;}
#chat{max-width:1000px;height:70vh;overflow-y:auto;margin:20px auto;padding:20px;background:white;border-radius:18px;}
.msg{padding:14px;margin:10px 0;border-radius:14px;white-space:pre-wrap;line-height:2;}
.user{background:#e2f1e8;}
.ai{background:#f7f0e5;}
#inputbox{max-width:1000px;margin:auto;display:flex;gap:10px;}
textarea{flex:1;resize:none;border:1px solid #bbb;border-radius:12px;padding:14px;font-family:Tahoma;font-size:15px;}
button{width:100px;border:0;border-radius:12px;background:#67977c;color:white;font-size:15px;cursor:pointer;}
</style>
</head>
<body>
<header><h2>دستیار هوش مصنوعی (Agent)</h2><div>Qwen 2.5 7B • Tool Calling</div></header>
<div id="chat"></div>
<div id="inputbox">
<textarea id="input" rows="3" placeholder="پیام خود را بنویسید..."></textarea>
<button onclick="send()">ارسال</button>
</div>
<script>
function add(text,type){
  const d=document.createElement("div");
  d.className="msg "+type;
  d.textContent=text;
  document.getElementById("chat").appendChild(d);
  window.scrollTo(0,document.body.scrollHeight);
}
async function send(){
  const box=document.getElementById("input");
  const text=box.value.trim();
  if(!text) return;
  add(text,"user");
  box.value="";
  add("در حال پردازش...","ai");
  try{
    const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text})});
    const data=await r.json();
    const chat=document.getElementById("chat");
    chat.removeChild(chat.lastChild);
    add(data.response || data.error,"ai");
  }catch(e){ add("خطا: "+e,"ai"); }
}
document.getElementById("input").addEventListener("keydown",function(e){
  if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); send(); }
});
</script>
</body>
</html>
"""


# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        user = request.json.get("message", "").strip()
        if not user:
            return jsonify({"response": "لطفاً پیام خود را وارد کنید."})

        if user.startswith("یادداشت کن ") or user.startswith("ذخیره کن "):
            prefix_len = len("یادداشت کن ") if user.startswith("یادداشت کن ") else len("ذخیره کن ")
            save_memory(user[prefix_len:].strip())
            return jsonify({"response": "در حافظه دائمی ذخیره شد."})

        if user == "حافظه":
            return jsonify({"response": get_memory()})

        answer, steps_log = run_agent(user)
        return jsonify({"response": answer, "steps": steps_log})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("================================")
    print("AI Assistant - AGENT MODE")
    print("Model:", MODEL)
    print("http://127.0.0.1:5000")
    print("================================")
    app.run(host="127.0.0.1", port=5000, debug=False)
