import os
import asyncio
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
TOKEN = os.getenv("TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"

# --- SERVER DUY TRÌ PORT ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("Bot đang chạy ở chế độ Polling!".encode('utf-8'))

    def log_message(self, format, *args):
        return  

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health Check Server đã khởi chạy trên Port: {port}")
    server.serve_forever()

# --- KHUÔN MẪU JS ---
JS_TEMPLATE = """// ========= ID ========= //
const mapping = {{
  '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip+watch_vip'],
  'Locket': ['Gold']
}};

// =========  Phần cố định  ========= // 
var ua=$request.headers["User-Agent"]||$request.headers["user-agent"],obj=JSON.parse($response.body);

obj.Attention="Chúc mừng bạn! Vui lòng không bán hoặc chia sẻ cho người khác!";

var {user}={{
  is_sandbox:!1,
  ownership_type:"PURCHASED",
  billing_issues_detected_at:null,
  period_type:"normal",
  expires_date:"2999-12-18T01:04:17Z",
  grace_period_expires_date:null,
  unsubscribe_detected_at:null,
  original_purchase_date:\"{date}T01:04:18Z\",
  purchase_date:\"{date}T01:04:17Z\",
  store:\"app_store\"
}};

var {user}_sub={{
  grace_period_expires_date:null,
  purchase_date:\"{date}T01:04:17Z\",
  product_identifier:\"com.{user}.premium.yearly\",
  expires_date:\"2999-12-18T01:04:17Z\"
}};

const match=Object.keys(mapping).find(e=>ua.includes(e));

if(match){{
  let[e,s]=mapping[match];
  s?({user}_sub.product_identifier=s,obj.subscriber.subscriptions[s]={user}):obj.subscriber.subscriptions[\"com.{user}.premium.yearly\"]={user},obj.subscriber.entitlements[e]={user}_sub
}}else{{
  obj.subscriber.subscriptions[\"com.{user}.premium.yearly\"]={user};
  obj.subscriber.entitlements.pro={user}_sub
}}

$done({{body:JSON.stringify(obj)}});"""

# --- KHUÔN MẪU MODULE ---
MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By {user} (Hết hạn: 2999-12-18)

[Script]
# ~ By {user}
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60

deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/locket_/main/Locket_NDTT/deleteHeader.js, timeout=60

[MITM]
hostname = %APPEND% api.revenuecat.com"""

# --- HÀM XỬ LÝ GITHUB ---
def push_to_gh(repo, path, content, msg):
    try:
        f = repo.get_contents(path, ref="main")
        repo.update_file(path, msg, content, f.sha, branch="main")
    except Exception:
        repo.create_file(path, msg, content, branch="main")

# --- LỆNH BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot đã sẵn sàng!\nGõ /hdsd để xem hướng dẫn.")

async def hdsd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cú pháp: `/get user | yyyy-mm-dd`\nVí dụ: `/get ndtt | 2025-01-16`", parse_mode='Markdown')

async def get_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        return await update.message.reply_text("⚠️ Sai cú pháp! Gõ mẫu: `/get trung | 2025-01-16`")
    
    try:
        user, date = [p.strip() for p in raw_text.split("|")]
        js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
        js_raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"

        status_msg = await update.message.reply_text("⏳ Đang xử lý GitHub...")

        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        
        push_to_gh(repo, js_p, JS_TEMPLATE.format(user=user, date=date), f"JS {user}")
        await asyncio.sleep(1)
        
        push_to_gh(repo, mod_p, MODULE_TEMPLATE.format(user=user, js_url=js_raw_url), f"Mod {user}")

        await status_msg.edit_text(f"✅ Thành công!\nLink: `https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# --- KHỞI CHẠY CHÍNH ---
async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("hdsd", hdsd))
    application.add_handler(CommandHandler("get", get_bundle))

    # 3. XỬ LÝ WEBHOOK & CONFLICT:
    print("🧹 Đang dọn dẹp Webhook cũ...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)

    # 4. Bắt đầu Polling
    print("🚀 Bot đang bắt đầu nhận tin nhắn (Polling)...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot đã dừng.")
