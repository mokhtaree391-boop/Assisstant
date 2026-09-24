from pathlib import Path
from flask import request, jsonify
from werkzeug.utils import secure_filename
import uuid

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED = {
    "pdf", "docx", "txt",
    "csv", "json", "xlsx", "xls",
    "md", "py", "log", "html", "xml",
    "jpg", "jpeg", "png", "webp", "bmp", "gif"
}

def register_upload(app):

    @app.route("/upload", methods=["POST"])
    def upload_file():
        if "file" not in request.files:
            return jsonify({"success": False, "error": "فایلی انتخاب نشده است"}), 400

        f = request.files["file"]

        if not f.filename:
            return jsonify({"success": False, "error": "نام فایل نامعتبر است"}), 400

        ext = f.filename.rsplit(".", 1)[-1].lower()

        if ext not in ALLOWED:
            return jsonify({
                "success": False,
                "error": f"فرمت .{ext} پشتیبانی نمی‌شود. فرمت‌های مجاز: {', '.join(sorted(ALLOWED))}"
            }), 400

        filename = secure_filename(f.filename)

        # اگر نام فایل فقط شامل حروف فارسی/یونیکد بود، secure_filename ممکن است آن را خالی کند
        if not filename or filename == f".{ext}":
            filename = f"{uuid.uuid4().hex[:8]}.{ext}"

        target = UPLOAD_DIR / filename

        f.save(target)

        return jsonify({
            "success": True,
            "filename": filename
        })
