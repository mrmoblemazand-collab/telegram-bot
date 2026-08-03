import logging
import json
import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN تنظیم نشده است!")


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from api_handler import PanelAPI, test_panel_connection

logging.basicConfig(level=logging.INFO)

TOKENS_FILE = "panel_tokens.json"
TOKEN_INPUT, PANEL_SELECT, USERNAME_INPUT, DATA_LIMIT_INPUT, DAYS_INPUT = range(5)

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی اصلی"""
    keyboard = [
        [InlineKeyboardButton("➕ اضافه کردن توکن", callback_data="add_token")],
        [InlineKeyboardButton("✅ تست اتصال", callback_data="test_connection")],
        [InlineKeyboardButton("👤 ایجاد اکاونت", callback_data="create_account")],
        [InlineKeyboardButton("📋 لیست توکن‌ها", callback_data="list_tokens")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *مدیریت پنل‌های VPN*\n\n"
        "چه کار می‌خوای؟",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_token":
        keyboard = [
            [InlineKeyboardButton("Marzban", callback_data="panel_marzban")],
            [InlineKeyboardButton("3x-ui", callback_data="panel_3xui")],
            [InlineKeyboardButton("Luffy Panel", callback_data="panel_luffy")],
            [InlineKeyboardButton("PasarGuard", callback_data="panel_pasarguard")],
            [InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔑 *کدام پنل؟*\n\n"
            "_توکن یا URL + Token رو بفرست_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("panel_"):
        panel = query.data.replace("panel_", "")
        context.user_data["selected_panel"] = panel
        
        guide = {
            "marzban": "فرمت: `http://panel-url/api-token`",
            "3xui": "فرمت: `http://panel-url:port/session-cookie`",
            "luffy": "فرمت: `http://panel-url`",
            "pasarguard": "فرمت: `http://panel-url`"
        }
        
        await query.edit_message_text(
            f"🔗 *توکن {panel.upper()} رو بفرست*\n\n"
            f"_{guide.get(panel, 'بفرست')}_",
            parse_mode="Markdown"
        )
        return TOKEN_INPUT
    
    elif query.data == "test_connection":
        tokens = load_tokens()
        if not tokens:
            await query.edit_message_text("❌ هنوز توکنی اضافه نشده")
            return
        
        keyboard = [[InlineKeyboardButton(p.upper(), callback_data=f"test_{p}")] 
                    for p in tokens.keys()]
        keyboard.append([InlineKeyboardButton("❌ بازگشت", callback_data="back_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("🔗 کدام پنل رو تست کنم؟", reply_markup=reply_markup)
    
    elif query.data.startswith("test_"):
        panel = query.data.replace("test_", "")
        tokens = load_tokens()
        token = tokens.get(panel)
        
        await query.edit_message_text(f"⏳ درحال تست {panel}...")
        
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
        
        await query.edit_message_text("👤 *اکاونت برای کدام پنل؟*", 
                                     reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data.startswith("create_"):
        panel = query.data.replace("create_", "")
        context.user_data["create_panel"] = panel
        
        await query.edit_message_text(
            f"👤 *نام کاربری برای {panel}:*\n\n"
            f"_(فقط حروف، اعداد و خط تیره)_",
            parse_mode="Markdown"
        )
        return USERNAME_INPUT
    
    elif query.data == "list_tokens":
        tokens = load_tokens()
        if not tokens:
            await query.edit_message_text("❌ توکنی ذخیره نشده")
            return
        
        text = "📋 *توکن‌های ذخیره‌شده:*\n\n"
        for panel, token in tokens.items():
            text += f"🔹 *{panel.upper()}*\n`{token[:30]}...`\n\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "back_menu":
        await start(update, context)

async def handle_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توکن"""
    token = update.message.text.strip()
    panel = context.user_data.get("selected_panel")
    
    if not panel:
        await update.message.reply_text("❌ ابتدا پنل رو انتخاب کن: /start")
        return
    
    tokens = load_tokens()
    tokens[panel] = token
    save_tokens(tokens)
    
    await update.message.reply_text(
        f"✅ *توکن {panel.upper()} ذخیره شد!*\n\n"
        f"دستور /start برای ادامه",
        parse_mode="Markdown"
    )

async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام کاربری"""
    username = update.message.text.strip()
    context.user_data["create_username"] = username
    
    await update.message.reply_text(
        "💾 *حجم دیتا (GB):*\n\n"
        "_(مثال: 10 یا 50)_",
        parse_mode="Markdown"
    )
    return DATA_LIMIT_INPUT

async def handle_data_limit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت حجم دیتا"""
    try:
        data_limit = int(update.message.text.strip())
        context.user_data["create_data_limit"] = data_limit
        
        await update.message.reply_text(
            "📅 *مدت اعتبار (روز):*\n\n"
            "_(مثال: 30 یا 90)_",
            parse_mode="Markdown"
        )
        return DAYS_INPUT
    except ValueError:
        await update.message.reply_text("❌ فقط عدد درست وارد کن!")
        return DATA_LIMIT_INPUT

async def handle_days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مدت زمان و ایجاد اکاونت"""
    try:
        days = int(update.message.text.strip())
        
        panel = context.user_data.get("create_panel")
        username = context.user_data.get("create_username")
        data_limit = context.user_data.get("create_data_limit")
        
        tokens = load_tokens()
        token = tokens.get(panel)
        
        await update.message.reply_text(f"⏳ *درحال ایجاد اکاونت...*", parse_mode="Markdown")
        
        api = PanelAPI(panel, token)
        result = api.create_account(username, data_limit, days)
        
        if result.get("success"):
            text = (
                f"✅ *اکاونت ایجاد شد!*\n\n"
                f"📌 پنل: `{panel.upper()}`\n"
                f"👤 نام: `{username}`\n"
                f"💾 دیتا: `{data_limit} GB`\n"
                f"📅 مدت: `{days} روز`"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {result.get('error', 'خطا ناشناخته')}", parse_mode="Markdown")
        
        context.user_data.clear()
        await update.message.reply_text("دستور /start برای ادامه")
        
    except ValueError:
        await update.message.reply_text("❌ فقط عدد درست وارد کن!")
        return DAYS_INPUT

def main():
    """اجرای بات"""
    application = Application.builder().token(BOT_TOKEN).build()
    # ... بقیه کد
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler برای جریان گفتگو
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
    
    print("✅ بات در حال اجرا است...")
    application.run_polling()

if __name__ == "__main__":
    main()