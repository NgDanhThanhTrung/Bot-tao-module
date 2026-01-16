import os
import time
import asyncio
import threading
from flask import Flask, request
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from waitress import serve

# --- CẤU HÌNH ---
TOKEN = os.getenv("TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") 

app_web = Flask(__name__)

# Khởi tạo Application của Telegram
application = ApplicationBuilder().token(TOKEN).build()

# --- LOGIC XỬ LÝ GITHUB ---
JS_TEMPLATE = """// JS Content for {user} - Date: {date}"""
MODULE_TEMPLATE = """// Module for {user} - JS: {js_url}"""

def push_to_gh(repo, path, content, msg):
    try:
        f = repo.get_contents(path, ref="main")
        repo.update_file(path, msg, content, f.sha, branch="main")
    except Exception:
        repo.create_file(path, msg, content, branch="main")

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👋 Chào {update.effective_user.first_name}!\nCú pháp: `/get user | yyyy-mm-dd`")

async def get_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = " ".join(context.args)
    if not raw_text or "|" not in raw_text:
        return await update.message.reply_text("⚠️ Cú pháp: `/get user | date`")
    
    try:
        user, date = [p.strip() for p in raw_text.split("|")]
        js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        mod_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}"

        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        push_to_gh(repo, js_p, JS_TEMPLATE.format(user=user, date=date), f"JS {user}")
        time.sleep(1)
        push_to_gh(repo, mod_p, MODULE_TEMPLATE.format(user=user, js_url=js_url), f"Mod {user}")

        await update.message.reply_text(f"✅ Thành công!\n🔗 Link: `{mod_url}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# Đăng ký handler vào application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("get", get_bundle))

# --- ROUTE XỬ LÝ WEBHOOK ---
@app_web.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    """Nhận và xử lý dữ liệu từ Telegram gửi về."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Sử dụng loop chính để xử lý update, tránh lỗi Runtime
        loop = asyncio.get_event_loop()
        loop.create_task(application.process_update(update))
        return "OK", 200
    return "Forbidden", 403

@app_web.route('/')
def health():
    return "Bot Webhook is Live!", 200

# --- KHỞI CHẠY HỆ THỐNG ---
async def setup_bot():
    """Khởi tạo trạng thái bot và thiết lập Webhook."""
    await application.initialize()
    await application.start()
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{TOKEN}"
        await application.bot.set_webhook(webhook_url)
        print(f"✅ Webhook đã được set: {webhook_url}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    
    # 1. Chạy tiến trình khởi tạo bot
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(setup_bot())
    
    # 2. Chạy Flask server bằng Waitress
    print(f"🚀 Server đang chạy tại cổng {port}...")
    serve(app_web, host='0.0.0.0', port=port)
