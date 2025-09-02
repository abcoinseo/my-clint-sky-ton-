import time
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# ---------------- CONFIG ----------------
BOT_TOKEN = "8418101664:AAGUUWpQVhrueHoP97W5laKOOlJ1LNKGQm8"
FIREBASE_DB_URL = "https://skytasktonbot-default-rtdb.firebaseio.com"
REFERRAL_EARNING_AMOUNT = 0.01
DAILY_BONUS = 0.001
MIN_WITHDRAW = 0.01
BOT_USERNAME = "SkyTaskTon_bot"

BANNER_URL = "https://i.postimg.cc/yNJ7n500/013213ab-a770-40cd-93c5-487045ad4a32.jpg"

# ---------------- FIREBASE INIT ----------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
users_ref = db.reference("users")
withdrawals_ref = db.reference("withdrawals")

# ---------------- HELPERS ----------------
def get_user(chat_id: str):
    return users_ref.child(chat_id).get()

def update_user(chat_id: str, data: dict):
    users_ref.child(chat_id).update(data)

def referral_link(chat_id: str):
    return f"https://t.me/{BOT_USERNAME}?start={chat_id}"

def number_format(num):
    return f"{num:,.4f}" if num else "0"

def get_top_users(limit=10):
    all_users = users_ref.get() or {}
    sorted_users = sorted(all_users.values(), key=lambda x: x.get("balance", 0), reverse=True)
    return sorted_users[:limit]

def daily_bonus():
    top3 = get_top_users(3)
    for user in top3:
        new_balance = user.get("balance", 0) + DAILY_BONUS
        update_user(user["chatId"], {"balance": new_balance})

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    args = context.args
    referred_by = args[0] if args else None

    user = get_user(chat_id)
    if not user:
        user = {
            "chatId": chat_id,
            "username": update.effective_user.username or update.effective_user.first_name,
            "balance": 0.0,
            "referrals": 0,
            "referredBy": None,
            "wallet": None,
            "lastWithdrawal": 0
        }
        update_user(chat_id, user)
    else:
        update_user(chat_id, {"username": update.effective_user.username or update.effective_user.first_name})

    # Referral bonus
    if referred_by and referred_by != chat_id and not user.get("referredBy"):
        ref_user = get_user(referred_by)
        if ref_user:
            update_user(referred_by, {
                "balance": ref_user.get("balance", 0) + REFERRAL_EARNING_AMOUNT,
                "referrals": ref_user.get("referrals", 0) + 1
            })
            update_user(chat_id, {"referredBy": referred_by})
            await context.bot.send_message(ref_user["chatId"], f"🚀 You earned {REFERRAL_EARNING_AMOUNT} Ton! New user @{user['username']} joined.")

    # Welcome message with buttons
    keyboard = [
        [InlineKeyboardButton("Owner", url="https://t.me/Cryptoairdropgiveaway1")],
        [InlineKeyboardButton("Developer", url="https://t.me/ABstudioseo")],
        [InlineKeyboardButton("🌐 Community", url="https://t.me/CryptoAirDrop384")],
        [InlineKeyboardButton("📊 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = f"🐸 Welcome to <b>Sky Task Ton</b>, @{update.effective_user.username or 'User'}!\n\nEarn and play with Ton coins!\n\nInvite friends using your referral link:\n{referral_link(chat_id)}"
    await context.bot.send_photo(chat_id=chat_id, photo=BANNER_URL, caption=welcome_text, parse_mode="HTML", reply_markup=reply_markup)

# ---------------- MAIN MENU ----------------
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("📣 Refer", callback_data="refer")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("📜 History", callback_data="history")]
    ]
    await context.bot.send_message(chat_id, "🔹 Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- CALLBACK HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    user = get_user(chat_id)
    data = query.data

    if data == "main_menu":
        await main_menu(update, context)

    elif data == "profile":
        text = (
            f"👤 User: @{user.get('username', 'N/A')}\n"
            f"🆔 ID: {user.get('chatId', chat_id)}\n\n"
            f"💰 Balance: {number_format(user.get('balance', 0))} Ton\n"
            f"🤝 Referrals: {number_format(user.get('referrals', 0))}\n\n"
            f"🔗 Referral Link:\n{referral_link(chat_id)}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "withdraw":
        if not user.get("wallet"):
            await query.message.edit_text("❌ Please set your wallet first using /withdraw <wallet>")
        else:
            text = f"💸 Withdraw\nCurrent Balance: {number_format(user.get('balance',0))} Ton\nMinimum Withdraw: {MIN_WITHDRAW} Ton\nSend /withdraw <amount> to withdraw."
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "history":
        history = withdrawals_ref.order_by_child("chatId").equal_to(chat_id).get() or {}
        if not history:
            msg = "📜 No withdrawal history found."
        else:
            msg = "📜 Withdraw History:\n\n"
            sorted_history = sorted(history.values(), key=lambda x: x["timestamp"], reverse=True)
            for h in sorted_history[:10]:
                status_icon = "✅" if h["status"]=="COMPLETED" else "⏳"
                msg += f"{status_icon} {h['amount']} Ton → {h['wallet']}\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "refer":
        text = f"📣 Invite friends and earn {REFERRAL_EARNING_AMOUNT} Ton!\nYour link: {referral_link(chat_id)}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "leaderboard":
        top_users = get_top_users(10)
        msg = "🏆 Leaderboard Top 10:\n\n"
        for i, u in enumerate(top_users, 1):
            msg += f"{i}. @{u.get('username','N/A')} - {number_format(u.get('balance',0))} Ton\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- /WITHDRAW COMMAND ----------------
async def withdraw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    if not user:
        return await update.message.reply_text("❌ Please /start first.")
    if not context.args:
        return await update.message.reply_text("❌ Usage: /withdraw <wallet|amount>")
    arg = context.args[0]

    # Set wallet
    if arg.startswith("UQ") or arg.startswith("EQ"):
        update_user(chat_id, {"wallet": arg})
        return await update.message.reply_text(f"✅ Wallet set to: {arg}")

    # Withdraw amount
    try:
        amount = float(arg)
    except ValueError:
        return await update.message.reply_text("❌ Invalid input.")

    if amount < MIN_WITHDRAW:
        return await update.message.reply_text(f"❌ Minimum withdraw is {MIN_WITHDRAW} Ton.")
    if amount > user.get("balance",0):
        return await update.message.reply_text("❌ Insufficient balance.")
    if not user.get("wallet"):
        return await update.message.reply_text("❌ Set wallet first using /withdraw <wallet>")

    # Deduct balance & add withdrawal record
    update_user(chat_id, {"balance": user.get("balance",0)-amount, "lastWithdrawal": int(time.time()*1000)})
    wid = f"W_{chat_id}_{int(time.time())}"
    withdrawals_ref.child(wid).set({
        "chatId": chat_id,
        "username": user.get("username"),
        "amount": amount,
        "wallet": user.get("wallet"),
        "status": "PENDING",
        "timestamp": int(time.time()*1000)
    })
    await update.message.reply_text(f"💸 Withdrawal submitted!\nAmount: {amount} Ton\nWallet: {user['wallet']}\nStatus: PENDING")

# ---------------- /PROFILE COMMAND ----------------
async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    if not user:
        return await update.message.reply_text("❌ Please /start first.")
    text = (
        f"👤 User: @{user.get('username', 'N/A')}\n"
        f"🆔 ID: {user.get('chatId', chat_id)}\n\n"
        f"💰 Balance: {number_format(user.get('balance', 0))} Ton\n"
        f"🤝 Referrals: {number_format(user.get('referrals', 0))}\n\n"
        f"🔗 Referral Link:\n{referral_link(chat_id)}"
    )
    await update.message.reply_text(text)

# ---------------- /REFER COMMAND ----------------
async def refer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(f"📣 Invite friends and earn {REFERRAL_EARNING_AMOUNT} Ton!\nYour link: {referral_link(chat_id)}")

# ---------------- /HELP COMMAND ----------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "SkyTaskTon Commands:\n"
        "/start - Start bot\n"
        "/profile - Show profile\n"
        "/refer - Get referral link\n"
        "/withdraw - Withdraw balance / set wallet\n"
        "/help - Show this help\n"
    )

# ---------------- APP INIT ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("withdraw", withdraw_cmd))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("profile", profile_cmd))
app.add_handler(CommandHandler("refer", refer_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

print("🚀 SkyTaskTon bot running...")
app.run_polling()
