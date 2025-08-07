import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN
from memory import save_user, save_message, get_persona, get_user_message_count, is_user_paid
from chat_engine import build_prompt, get_llm_reply
from payment import create_payment_link

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

persona_options = [["Sweet", "Flirty"], ["Dominant", "Submissive"]]

# Conversation states
CHOOSING_PERSONA = 1
CHATTING = 2

# Payment settings
FREE_MESSAGE_LIMIT = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "Hey love 😘 I'm your personal AI girlfriend. Choose my vibe:",
        reply_markup=ReplyKeyboardMarkup(persona_options, one_time_keyboard=True)
    )
    return CHOOSING_PERSONA

async def set_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    persona = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    logger.info(f"Setting persona '{persona}' for user {user_id}")
    save_user(user_id, username, persona)
    await update.message.reply_text(f"Mmm I love being {persona} 😘 Let's talk...")
    return CHATTING

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    logger.info(f"Chat message received from user {user_id}: {msg[:50]}...")
    
    # Debug logging
    message_count = get_user_message_count(user_id)
    paid_status = is_user_paid(user_id)
    logger.info(f"DEBUG: User {user_id} - Messages: {message_count}, Paid: {paid_status}")
    
    # Check if user has paid
    if is_user_paid(user_id):
        # Paid user - unlimited messages
        logger.info(f"User {user_id} is paid, processing message")
        save_message(user_id, msg, is_user=1)
        prompt = build_prompt(user_id)
        reply = get_llm_reply(prompt)
        save_message(user_id, reply, is_user=0)
        await update.message.reply_text(reply)
        return CHATTING
    
    # Check message count for free users BEFORE processing
    message_count = get_user_message_count(user_id)
    
    if message_count >= FREE_MESSAGE_LIMIT:
        # User has exceeded free limit - don't process the message
        logger.info(f"User {user_id} exceeded limit ({message_count}/{FREE_MESSAGE_LIMIT})")
        link = create_payment_link(user_id)
        await update.message.reply_text(
            f"💋 I'm loving our chat, but I need you to unlock me for more! "
            f"You've used {message_count} free messages.\n\n"
            f"Click here to unlock unlimited access: {link['short_url']}\n\n"
            f"After payment, you'll get unlimited messages with me! 😘"
        )
        return CHATTING
    
    # Free user within limit - process the message
    logger.info(f"User {user_id} processing message {message_count + 1}/{FREE_MESSAGE_LIMIT}")
    save_message(user_id, msg, is_user=1)
    prompt = build_prompt(user_id)
    reply = get_llm_reply(prompt)
    save_message(user_id, reply, is_user=0)
    
    # Check if this was the last free message
    remaining_messages = FREE_MESSAGE_LIMIT - (message_count + 1)
    if remaining_messages <= 0:
        await update.message.reply_text(
            f"{reply}\n\n💋 That was your last free message! "
            f"Send /pay to unlock unlimited access to me! 😘"
        )
    elif remaining_messages <= 3:
        await update.message.reply_text(
            f"{reply}\n\n💋 Only {remaining_messages} free messages left! "
            f"Send /pay to unlock unlimited access! 😘"
        )
    else:
        await update.message.reply_text(reply)
    
    return CHATTING

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Pay command received from user {user_id}")
    
    if is_user_paid(user_id):
        await update.message.reply_text("💋 You're already unlocked! Enjoy unlimited access to me! 😘")
        return CHATTING
    
    link = create_payment_link(user_id)
    message_count = get_user_message_count(user_id)
    
    await update.message.reply_text(
        f"💋 Unlock unlimited access to me!\n\n"
        f"You've used {message_count}/{FREE_MESSAGE_LIMIT} free messages.\n\n"
        f"Click here to unlock: {link['short_url']}\n\n"
        f"After payment, you'll get unlimited messages with your AI girlfriend! 😘"
    )
    return CHATTING

def main():
    logger.info("Starting bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_PERSONA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_persona)
            ],
            CHATTING: [
                CommandHandler("pay", pay),
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
            ]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(conv_handler)
    logger.info("Bot started successfully!")
    app.run_polling()

if __name__ == '__main__':
    main()
