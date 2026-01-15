import os, time, threading
from flask import Flask
from datetime import datetime
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Health Check cho Render Web Service ---
app_web = Flask(__name__)
@app_web.route('/')
def health(): return "Bot is live!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

# --- Cấu hình ---
TOKEN, GH_TOKEN = os.getenv("TOKEN"), os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"

JS_TEMPLATE = """const mapping = {{
  '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip', 'watch_vip'],
  'Locket': ['Gold', 'com.{user}.premium.yearly']
}};
const ua = $request.headers["User-Agent"] || $request.headers["user-agent"];
let obj = JSON.parse($response.body);
obj.subscriber = obj.subscriber || {{}};
obj.subscriber.entitlements = obj.subscriber.entitlements || {{}};
obj.subscriber.subscriptions = obj.subscriber.subscriptions || {{}};
const premiumInfo = {{
  is_sandbox: false,
  ownership_type: "PURCHASED",
  billing_issues_detected_at: null,
  period_type: "normal",
  expires_date: "2999-12-18T01:04:17Z",
  original_purchase_date: "{date}T01:04:17Z",
  purchase_date: "{date}T01:04:17Z",
  store: "app_store"
}};
const entitlementInfo = {{
  grace_period_expires_date: null,
  purchase_date: "{date}T01:04:17Z",
  product_identifier: "com.{user}.premium.yearly",
  expires_date: "2999-12-18T01:04:17Z"
}};
const match = Object.keys(mapping).find(e => ua.includes(e));
if (match) {{
  let [entKey, subKey] = mapping[match];
  let finalSubKey = subKey || "com.{user}.premium.yearly";
  entitlementInfo.product_identifier = finalSubKey;
  obj.subscriber.subscriptions[finalSubKey] = premiumInfo;
  obj.subscriber.entitlements[entKey] = entitlementInfo;
}} else {{
  obj.subscriber.subscriptions["com.{user}.premium.yearly"] = premiumInfo;
  obj.subscriber.entitlements["Gold"] = entitlementInfo;
  obj.subscriber.entitlements["pro"] = entitlementInfo;
}}
obj.Attention = "Chào {user}! Chúc mừng bạn đã kích hoạt thành công!";
$done({{ body: JSON.stringify(obj) }});"""

MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By NgDanhThanhTrung
[Script]
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60
deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/modules/main/LOCKET/deleteHeader.js, timeout=60
[MITM]
hostname = %APPEND% api.revenuecat.com"""

def push_to_gh(repo, path, content, msg):
    try:
        f = repo.get_contents(path, ref="main")
        repo.update_file(path, msg, content, f.sha, branch="main")
    except:
        repo.create_file(path, msg, content, branch="main")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👋 Chào {update.effective_user.first_name}!\nCú pháp: `/get user | yyyy-mm-dd`", parse_mode='Markdown')

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

        # Link được bọc trong backticks để chạm là sao chép
        await update.message.reply_text(
            f"✅ **Đã tạo thành công!**\n\n"
            f"👤 User: `{user}`\n"
            f"📅 Date: `{date}`\n\n"
            f"🔗 **Link Module (Chạm để sao chép):**\n`{mod_url}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get_bundle))
    app.run_polling()
