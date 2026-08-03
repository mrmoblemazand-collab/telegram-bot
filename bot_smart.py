
import logging
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from api_handler import PanelAPI, test_panel_connection
from railway_api import full_deploy
from github import Github
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

# ============== Config ==============
BOT_TOKEN = os.getenv("BOT_TOKEN")
TOKENS_FILE = "deployed.json"

PANELS = {
    "marzban": {
        "name": "Marzban",
        "docker": """FROM ghasemloo/marzban:latest
EXPOSE 8000
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000
CMD ["marzban"]"""
    },
    "3xui": {
        "name": "3x-ui",
        "docker": """FROM mhsanaei/3x-ui:latest
EXPOSE 54321
CMD ["bash", "entrypoint.sh"]"""
    }
}

def load_config():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return {"github": None, "railway": None, "panels": {}}

def save_config(cfg):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

# ============== Main Menu ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    
    keyboard = []
    
    if not cfg["github"] or not cfg["railway"]:
        keyboard.append([InlineKeyboardButton("⚙️ Setup Tokens", callback_data="setup")])
    else:
        keyboard.append([InlineKeyboardButton("🚀 Deploy Panel", callback_data="deploy_menu")])
        keyboard.append([InlineKeyboardButton("📋 Deployed Panels", callback_data="list_panels")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "❌ Tokens نیست" if not cfg["github"] else "✅ آماده"
    
    await update.message.reply_text(
        f"🤖 *Smart Panel Manager*\n\n"
        f"وضعیت: {status}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ============== Setup ==============

async def setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "setup":
        keyboard = [
            [InlineKeyboardButton("1️⃣ GitHub Token", callback_data="setup_github")],
            [InlineKeyboardButton("2️⃣ Railway Token", callback_data="setup_railway")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Setup Tokens*\n\n"
            "Tokens رو بده:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data == "setup_github":
        context.user_data["setup_type"] = "github"
        await query.edit_message_text(
            "🔑 GitHub Token رو بفرست:\n\n"
            "[github.com/settings/tokens](https://github.com/settings/tokens)",
            parse_mode="Markdown"
        )
    
    elif query.data == "setup_railway":
        context.user_data["setup_type"] = "railway"
        await query.edit_message_text(
            "🔑 Railway Token رو بفرست:\n\n"
            "[railway.app/account/tokens](https://railway.app/account/tokens)",
            parse_mode="Markdown"
        )

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    setup_type = context.user_data.get("setup_type")
    
    if not setup_type:
        await update.message.reply_text("ابتدا /start بزن")
        return
    
    cfg = load_config()
    
    if setup_type == "github":
        cfg["github"] = token
        msg = "✅ GitHub Token ذخیره شد"
    else:
        cfg["railway"] = token
        msg = "✅ Railway Token ذخیره شد"
    
    save_config(cfg)
    context.user_data.pop("setup_type", None)
    
    await update.message.reply_text(msg + "\n\n/start")

# ============== Deploy ==============

async def deploy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "deploy_menu":
        keyboard = [
            [InlineKeyboardButton("Marzban", callback_data="deploy_marzban")],
            [InlineKeyboardButton("3x-ui", callback_data="deploy_3xui")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 کدام پنل؟",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("deploy_"):
        panel = query.data.replace("deploy_", "")
        cfg = load_config()
        
        if not cfg["github"] or not cfg["railway"]:
            await query.edit_message_text("❌ Tokens تنظیم نشده")
            return
        
        await query.edit_message_text(
            f"⏳ {PANELS[panel]['name']} Deploy می‌شه...\n\n"
            f"مراحل:\n"
            f"1️⃣ GitHub Repo\n"
            f"2️⃣ Railway Project\n"
            f"3️⃣ Deploy خودکار\n\n"
            f"۲-۳ دقیقه..."
        )
        
        # Deploy
        try:
            g = Github(cfg["github"])
            user = g.get_user()
            
            repo_name = f"panel-{panel}-{int(time.time())}"
            repo = user.create_repo(repo_name, private=False)
            
            # Dockerfile
            repo.create_file("Dockerfile", "add", PANELS[panel]["docker"])
            repo.create_file(".gitignore", "add", "*.db\n*.sqlite\n.env\n")
            
            # Railway Deploy
            result = full_deploy(cfg["github"], cfg["railway"], panel, repo)
            
            if result["success"]:
                text = (
                    f"✅ *{PANELS[panel]['name']} Deploy شد!*\n\n"
                    f"🔗 URL:\n`{result['url']}`\n\n"
                    f"👤 Admin:\n"
                    f"`username: admin`\n"
                    f"`password: admin`"
                )
                
                # Save
                cfg["panels"][panel] = {
                    "url": result["url"],
                    "repo": result["repo"]
                }
                save_config(cfg)
            else:
                text = f"❌ خطا: {result['error']}"
            
            await query.edit_message_text(text, parse_mode="Markdown")
        
        except Exception as e:
            await query.edit_message_text(f"❌ {str(e)}")

async def list_panels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cfg = load_config()
    
    if not cfg["panels"]:
        await query.edit_message_text("❌ پنلی deploy نشده")
        return
    
    text = "📋 *Deploy شده:*\n\n"
    for panel, data in cfg["panels"].items():
        text += f"🔹 {panel.upper()}\n`{data['url']}`\n\n"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ============== Main ==============

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(setup_callback, pattern="^setup"))
    application.add_handler(CallbackQueryHandler(deploy_callback, pattern="^deploy"))
    application.add_handler(CallbackQueryHandler(list_panels, pattern="^list_panels"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))
    
    print("✅ Smart Bot Running...")
    application.run_polling()

if __name__ == "__main__":
    main()
