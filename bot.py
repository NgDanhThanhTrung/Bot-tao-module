import os
import time
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
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # URL của Render (ví dụ: https://bot-cua-ban.onrender.com)

app_web = Flask(__name__)
# Khởi tạo Application của Telegram
application = ApplicationBuilder().token(TOKEN).build()

# --- ROUTE XỬ LÝ WEBHOOK ---
@app_web.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    # Nhận dữ liệu từ Telegram gửi về
    update = Update.de_json(request.get_json(force=True), application.bot)
    # Xử lý update một cách không đồng bộ
    import asyncio
    asyncio.run(application.process_update(update))
    return "OK", 200

@app_web.route('/')
def health():
    return "Bot Webhook is Live!", 200

# --- LOGIC XỬ LÝ BOT (Giữ nguyên từ code cũ) ---
JS_TEMPLATE = """...""" # Nội dung JS của bạn
MODULE_TEMPLATE = """...""" # Nội dung Module của bạn

def push_to_gh(repo, path, content, msg):
    try:
        f = repo.get_contents(path, ref="main")
        repo.update_file(path, msg, content, f.sha, branch="main")
    except:
        repo.create_file(path, msg, content, branch="main")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👋 Chào {update.effective_user.first_name}!\nCú pháp: `/get user | yyyy-mm-dd`")

async def get_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Giữ nguyên logic xử lý GitHub như file cũ của bạn)
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

# Đăng ký handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("get", get_bundle))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    
    # Thiết lập Webhook với Telegram
    if RENDER_URL:
        webhook_path = f"{RENDER_URL}/{TOKEN}"
        # Chạy một thread nhỏ để set webhook khi khởi động
        import asyncio
        asyncio.run(application.bot.set_webhook(webhook_path))
        print(f"Webhook set to: {webhook_path}")
    
    # Chạy Flask server bằng Waitress
    serve(app_web, host='0.0.0.0', port=port)
