import logging
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from api_handler import PanelAPI, test_panel_connection
from github import Github
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKENS_FILE = "panel_tokens.json"
DEPLOYED_FILE = "deployed_panels.json"

# API Tokens
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")

TOKEN_INPUT, PANEL_SELECT, USERNAME_INPUT, DATA_LIMIT_INPUT, DAYS_INPUT = range(5)

# تعریف پنل‌ها
PANELS_CONFIG = {
    "marzban": {
        "name": "Marzban",
        "dockerfile": """FROM ghasemloo/marzban:latest
EXPOSE 8000
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000
CMD ["marzban"]"""
    },
    "3xui": {
        "name": "3x-ui",
        "dockerfile": """FROM mhsanaei/3x-ui:latest
EXPOSE 54321
ENV TZ=UTC
CMD ["bash", "entrypoint.sh"]"""
    },
    "luffy": {
        "name": "Luffy Panel",
        "dockerfile": """FROM python:3.11
WORKDIR /app
RUN git clone https://github.com/luffysxn/luffypanel . || true
RUN pip install -r requirements.txt 2>/dev/null || echo "No requirements"
EXPOSE 8000
CMD ["python", "app.py"]"""
    }
}

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def load_deployed():
    if os.path.exists(DEPLOYED_FILE):
        with open(DEPLOYED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_deployed(panels):
    with open(DEPLOYED_FILE, 'w') as f:
        json.dump(panels, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی اصلی"""
    keyboard = [
        [InlineKeyboardButton("🚀 Deploy خودکار پنل", callback_data="auto_deploy")],
        [InlineKeyboardButton("➕ اضافه کردن توکن دستی", callback_data="add_token")],
        [InlineKeyboardButton("✅ تست اتصال", callback_data="test_connection")],
        [InlineKeyboardButton("👤 ایجاد اکاونت", callback_data="create_account")],
        [InlineKeyboardButton("📋 لیست", callback_data="list_tokens")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *مدیریت پنل‌های VPN*\n\n"
        "انتخاب کن:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "auto_deploy":
        keyboard = [
            [InlineKeyboardButton("Marzban", callback_data="deploy_marzban")],
            [InlineKeyboardButton("3x-ui", callback_data="deploy_3xui")],
            [InlineKeyboardButton("Luffy Panel", callback_data="deploy_luffy")],
            [InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔧 *کدام پنل رو deploy کنم؟*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("deploy_"):
        panel_type = query.data.replace("deploy_", "")
        
        if not GITHUB_TOKEN or not RAILWAY_TOKEN:
            await query.edit_message_text(
                "❌ *API Tokens تنظیم نشده!*\n\n"
                "Railway Dashboard میرو و اینها رو اضافه کن:\n"
                "• `GITHUB_TOKEN`\n"
                "• `RAILWAY_TOKEN`",
                parse_mode="Markdown"
            )
            return
        
        await query.edit_message_text(
            f"⏳ *{PANELS_CONFIG[panel_type]['name']} deploy می‌شه...*\n\n"
            "_۲-۳ دقیقه طول می‌کشه..._",
            parse_mode="Markdown"
        )
        
        result = await deploy_panel_to_railway(panel_type)
        
        if result["success"]:
            text = (
                f"✅ *{PANELS_CONFIG[panel_type]['name']} Deploy شد!*\n\n"
                f"🔗 URL:\n`{result['url']}`\n\n"
                f"📝 Admin:\n"
                f"username: `admin`\n"
                f"password: `admin`\n\n"
                f"_رمز رو تغییر بده!_"
            )
            
            # ذخیره
            deployed = load_deployed()
            deployed[panel_type] = {
                "url": result['url'],
                "repo": result['repo'],
                "deployed_at": str(time.time())
            }
            save_deployed(deployed)
            
            # اضافه کردن توکن خودکار
            tokens = load_tokens()
            tokens[panel_type] = result['url']
            save_tokens(tokens)
        else:
            text = f"❌ خطا:\n{result['error']}"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "add_token":
        keyboard = [
            [InlineKeyboardButton("Marzban", callback_data="panel_marzban")],
            [InlineKeyboardButton("3x-ui", callback_data="panel_3xui")],
            [InlineKeyboardButton("Luffy", callback_data="panel_luffy")],
            [InlineKeyboardButton("PasarGuard", callback_data="panel_pasarguard")],
            [InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔑 *کدام پنل؟*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("panel_"):
        panel = query.data.replace("panel_", "")
        context.user_data["selected_panel"] = panel
        
        guide = {
            "marzban": "فرمت: `http://url/token`",
            "3xui": "فرمت: `http://url:port/cookie`",
            "luffy": "فرمت: `http://url`",
            "pasarguard": "فرمت: `http://url`"
        }
        
        await query.edit_message_text(
            f"🔗 *توکن {panel.upper()} رو بفرست*\n\n"
            f"_{guide.get(panel)}_",
            parse_mode="Markdown"
        )
        return TOKEN_INPUT
    
    elif query.data == "test_connection":
        tokens = load_tokens()
        if not tokens:
            await query.edit_message_text("❌ توکنی نیست")
            return
        
        keyboard = [[InlineKeyboardButton(p.upper(), callback_data=f"test_{p}")] 
                    for p in tokens.keys()]
        keyboard.append([InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("🔗 کدام پنل؟", reply_markup=reply_markup)
    
    elif query.data.startswith("test_"):
        panel = query.data.replace("test_", "")
        tokens = load_tokens()
        token = tokens.get(panel)
        
        await query.edit_message_text(f"⏳ تست {panel}...")
        
        result = test_panel_connection(panel, token)
        if result["success"]:
            await query.edit_message_text(f"✅ *{panel.upper()}*\n{result['message']}", parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ *{panel.upper()}*\n{result['error']}", parse_mode="Markdown")
    
    elif query.data == "create_account":
        tokens = load_tokens()
        if not tokens:
            await query.edit_message_text("❌ ابتدا توکن اضافه کن")
            return
        
        keyboard = [[InlineKeyboardButton(p.upper(), callback_data=f"create_{p}")] 
                    for p in tokens.keys()]
        keyboard.append([InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("👤 کدام پنل؟", reply_markup=reply_markup)
    
    elif query.data.startswith("create_"):
        panel = query.data.replace("create_", "")
        context.user_data["create_panel"] = panel
        
        await query.edit_message_text(f"👤 نام کاربری برای {panel}:")
        return USERNAME_INPUT
    
    elif query.data == "list_tokens":
        tokens = load_tokens()
        deployed = load_deployed()
        
        if not tokens and not deployed:
            await query.edit_message_text("❌ چیزی ذخیره نشده")
            return
        
        text = ""
        
        if deployed:
            text += "🚀 *Deploy شده:*\n"
            for panel, data in deployed.items():
                text += f"• {panel.upper()}\n"
        
        if tokens:
            text += "\n📋 *توکن‌ها:*\n"
            for panel, token in tokens.items():
                text += f"• {panel}: `{token[:25]}...`\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "back_menu":
        await start(update, context)

async def deploy_panel_to_railway(panel_type: str) -> dict:
    """Deploy Panel روی Railway"""
    try:
        # ۱. Repository ایجاد
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        
        repo_name = f"panel-{panel_type}-{int(time.time())}"
        repo = user.create_repo(repo_name, private=False, description=f"{panel_type} panel")
        
        # ۲. فایل‌ها
        dockerfile = PANELS_CONFIG[panel_type]["dockerfile"]
        repo.create_file("Dockerfile", "Add Dockerfile", dockerfile)
        repo.create_file(".gitignore", "Add gitignore", "*.db\n*.sqlite\n.env\n")
        repo.create_file("README.md", "Add README", f"# {PANELS_CONFIG[panel_type]['name']}\n\nDeployed on Railway")
        
        # ۳. URL نتیجه
        railway_url = f"https://{repo_name}-production.up.railway.app"
        
        return {
            "success": True,
            "url": railway_url,
            "repo": repo.clone_url
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

async def handle_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توکن"""
    token = update.message.text.strip()
    panel = context.user_data.get("selected_panel")
    
    if not panel:
        await update.message.reply_text("❌ ابتدا پنل رو انتخاب کن")
        return
    
    tokens = load_tokens()
    tokens[panel] = token
    save_tokens(tokens)
    
    await update.message.reply_text(
        f"✅ توکن {panel.upper()} ذخیره شد!\n\n/start",
        parse_mode="Markdown"
    )

async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام کاربری"""
    username = update.message.text.strip()
    context.user_data["create_username"] = username
    
    await update.message.reply_text("💾 حجم دیتا (GB):\n_(مثال: 10)_")
    return DATA_LIMIT_INPUT

async def handle_data_limit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت حجم"""
    try:
        data_limit = int(update.message.text.strip())
        context.user_data["create_data_limit"] = data_limit
        await update.message.reply_text("📅 مدت (روز):\n_(مثال: 30)_")
        return DAYS_INPUT
    except ValueError:
        await update.message.reply_text("❌ عدد درست وارد کن!")
        return DATA_LIMIT_INPUT

async def handle_days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ایجاد اکاونت"""
    try:
        days = int(update.message.text.strip())
        
        panel = context.user_data.get("create_panel")
        username = context.user_data.get("create_username")
        data_limit = context.user_data.get("create_data_limit")
        
        tokens = load_tokens()
        token = tokens.get(panel)
        
        await update.message.reply_text(f"⏳ درحال ایجاد...")
        
        api = PanelAPI(panel, token)
        result = api.create_account(username, data_limit, days)
        
        if result.get("success"):
            text = (
                f"✅ اکاونت ایجاد شد!\n\n"
                f"📌 پنل: `{panel.upper()}`\n"
                f"👤 نام: `{username}`\n"
                f"💾 دیتا: `{data_limit} GB`\n"
                f"📅 مدت: `{days} روز`"
            )
        else:
            text = f"❌ {result.get('error')}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        context.user_data.clear()
        
    except ValueError:
        await update.message.reply_text("❌ عدد درست وارد کن!")
        return DAYS_INPUT

def main():
    """اجرای بات"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^panel_")],
        states={
            TOKEN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token_input)],
            USERNAME_INPUT: [CallbackQueryHandler(button_callback), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input)],
            DATA_LIMIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_limit_input)],
            DAYS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days_input)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token_input))
    
    print("✅ بات هوشمند در حال اجرا است...")
    application.run_polling()

if __name__ == "__main__":
    main()
