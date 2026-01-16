import os
import time
import asyncio
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
application = ApplicationBuilder().token(TOKEN).build()
main_loop = None

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
  original_purchase_date:"{date}T01:04:18Z",
  purchase_date:"{date}T01:04:17Z",
  store:"app_store"
}};

var {user}_sub={{
  grace_period_expires_date:null,
  purchase_date:"{date}T01:04:17Z",
  product_identifier:"com.{user}.premium.yearly",
  expires_date:"2999-12-18T01:04:17Z"
}};

const match=Object.keys(mapping).find(e=>ua.includes(e));

if(match){{
  let[e,s]=mapping[match];
  s?({user}_sub.product_identifier=s,obj.subscriber.subscriptions[s]={user}):obj.subscriber.subscriptions["com.{user}.premium.yearly"]={user},obj.subscriber.entitlements[e]={user}_sub
}}else{{
  obj.subscriber.subscriptions["com.{user}.premium.yearly"]={user};
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

def push_to_gh(repo, path, content, msg):
    try:
        f = repo.get_contents(path, ref="main")
        repo.update_file(path, msg, content, f.sha, branch="main")
    except Exception:
        repo.create_file(path, msg, content, branch="main")

# --- LỆNH BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot đã sẵn sàng!\nGõ /hdsd để xem cách dùng.")

async def hdsd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cú pháp: `/get user | yyyy-mm-dd`", parse_mode='Markdown')

async def get_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        return await update.message.reply_text("⚠️ Gõ theo mẫu: `/get trung | 2025-01-16`")
    
    try:
        user, date = [p.strip() for p in raw_text.split("|")]
        js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
        js_raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"

        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        push_to_gh(repo, js_p, JS_TEMPLATE.format(user=user, date=date), f"JS {user}")
        time.sleep(1)
        push_to_gh(repo, mod_p, MODULE_TEMPLATE.format(user=user, js_url=js_raw_url), f"Mod {user}")

        await update.message.reply_text(f"✅ Xong! Link: `https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# --- WEBHOOK & APP ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hdsd", hdsd))
application.add_handler(CommandHandler("get", get_bundle))

@app_web.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if main_loop and main_loop.is_running():
        main_loop.call_soon_threadsafe(lambda: asyncio.create_task(application.process_update(update)))
    return "OK", 200

@app_web.route('/')
def health(): return "OK", 200

async def setup_bot():
    await application.initialize()
    await application.start()
    if RENDER_URL:
        # Tự động xóa Webhook cũ trước khi đặt mới để tránh nghẽn
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.bot.set_webhook(f"{RENDER_URL}/{TOKEN}")
        print(f"Webhook set to: {RENDER_URL}/{TOKEN}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    main_loop.run_until_complete(setup_bot())
    serve(app_web, host='0.0.0.0', port=port, threads=8)
