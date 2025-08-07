import logging
from telegram import Update, ReplyKeyboardMarkup, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from config import TELEGRAM_BOT_TOKEN
from memory import save_user, save_message, get_persona, get_user_message_count, is_user_paid, mark_user_paid
from chat_engine import build_prompt, get_llm_reply
from payment import is_user_paid_upi
from characters import character_manager
from stars_payment import stars_payment_manager
from ai_models import ai_model_manager

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_PERSONA = 1
CHATTING = 2

# Payment settings
FREE_MESSAGE_LIMIT = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot and show character selection"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"User {user_id} ({user_name}) started the bot")
    
    # Check if user has an active character
    active_char = character_manager.get_active_character(user_id)
    
    if active_char:
        # User has an active character, continue chatting
        await update.message.reply_text(
            f"👋 Welcome back, {user_name}! 😘\n\n"
            f"You're currently chatting with **{active_char['name']}** ({active_char['role']})\n\n"
            f"Just send me a message to continue our conversation! 💕\n\n"
            f"Send /characters to change characters",
            parse_mode='Markdown'
        )
        return CHATTING
    else:
        # Show character selection
        await show_characters(update, context)
        return CHOOSING_PERSONA

async def show_characters(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Show character selection menu"""
    user_id = update.effective_user.id
    
    message = character_manager.create_character_message(user_id, page)
    keyboard = character_manager.create_characters_keyboard(user_id, page)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

async def handle_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle character selection and unlock callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "close_characters":
        await query.edit_message_text("Character selection closed. Send /characters to open again!")
        return CHOOSING_PERSONA
    
    elif data.startswith("char_page:"):
        page = int(data.split(":")[1])
        await show_characters(update, context, page)
        return CHOOSING_PERSONA
    
    # Handle character unlock requests
    if data.startswith("unlock:"):
        character_id = int(data.split(":")[1])
        char = character_manager.get_character_by_id(character_id)
        
        if not char:
            await query.answer("Character not found!")
            return
        
        if char["is_locked"]:
            # Show unlock options
            keyboard = stars_payment_manager.create_unlock_keyboard(
                character_id, char["name"], char["price_stars"]
            )
            
            # Get AI model benefits
            ai_benefits = ai_model_manager.get_character_tier_benefits(char["price_stars"])
            
            await query.edit_message_text(
                f"🔒 **Unlock {char['name']}**\n\n"
                f"💫 Price: {char['price_stars']} Stars\n"
                f"🎭 Role: {char['role']}\n"
                f"📍 Region: {char['region']}\n"
                f"💬 Language: {char['language']}\n"
                f"🤖 {ai_benefits}\n\n"
                f"📝 {char['description']}\n\n"
                f"Click below to unlock with Telegram Stars!",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            # Character is already unlocked, select it
            character_manager.set_active_character(user_id, character_id)
            await query.edit_message_text(
                f"✅ **{char['name']} selected!**\n\n"
                f"🎭 Role: {char['role']}\n"
                f"📍 Region: {char['region']}\n"
                f"💬 Language: {char['language']}\n\n"
                f"Start chatting with {char['name']} now! 😘\n\n"
                f"Send /characters to change characters",
                parse_mode='Markdown'
            )
    
    # Handle character payment requests
    elif data.startswith("pay_character:"):
        parts = data.split(":")
        character_id = int(parts[1])
        stars_amount = int(parts[2])
        
        char = character_manager.get_character_by_id(character_id)
        if not char:
            await query.answer("Character not found!")
            return
        
        # Create Stars invoice for character unlock
        try:
            await context.bot.send_invoice(
                chat_id=user_id,
                title=f"🔒 Unlock {char['name']}",
                description=f"Unlock {char['name']} ({char['role']}) for unlimited chatting",
                payload=f"character_unlock:{character_id}",
                provider_token="",  # Empty for digital goods
                currency="XTR",
                prices=[LabeledPrice(f"Unlock {char['name']} ({stars_amount} Stars)", stars_amount)],
                start_parameter=f"character_{character_id}",
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                send_phone_number_to_provider=False,
                send_email_to_provider=False,
                is_flexible=False,
                disable_notification=False,
                protect_content=False,
                reply_to_message_id=None,
                allow_sending_without_reply=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Pay with Stars", pay=True)],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_payment")]
                ])
            )
            
            await query.answer("Payment invoice sent!")
            
        except Exception as e:
            logger.error(f"Error creating character unlock invoice: {e}")
            await query.answer("Error creating payment. Please try again!")
    
    # Handle unlimited access unlock requests
    elif data.startswith("unlock_unlimited:"):
        stars_amount = int(data.split(":")[1])
        
        # Create Stars invoice for unlimited access
        try:
            await context.bot.send_invoice(
                chat_id=user_id,
                title="🌟 Unlock Unlimited Access",
                description=f"Get unlimited access to all characters and premium AI models",
                payload=f"unlimited_access:{stars_amount}",
                provider_token="",  # Empty for digital goods
                currency="XTR",
                prices=[LabeledPrice(f"Unlimited Access ({stars_amount} Stars)", stars_amount)],
                start_parameter="unlimited_access",
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                send_phone_number_to_provider=False,
                send_email_to_provider=False,
                is_flexible=False,
                disable_notification=False,
                protect_content=False,
                reply_to_message_id=None,
                allow_sending_without_reply=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Pay with Stars", pay=True)],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_payment")]
                ])
            )
            
            await query.answer("Payment invoice sent!")
            
        except Exception as e:
            logger.error(f"Error creating unlimited access invoice: {e}")
            await query.answer("Error creating payment. Please try again!")
    
    # Handle character selection (already unlocked characters)
    elif data.startswith("select_char:"):
        character_id = data.split(":")[1]
        char = character_manager.get_character_by_id(character_id)
        
        if char and character_manager.set_active_character(user_id, character_id):
            await query.edit_message_text(
                f"🎉 You're now chatting with **{char['name']}**!\n\n"
                f"💬 {char['description']}\n\n"
                f"Start chatting with her! 😘\n\n"
                f"Send /characters to change your AI girlfriend anytime!",
                parse_mode='Markdown'
            )
            return CHATTING
        else:
            await query.answer("Failed to select character. Please try again.")
            return CHOOSING_PERSONA
    
    elif data.startswith("unlock_char:"):
        character_id = data.split(":")[1]
        char = character_manager.get_character_by_id(character_id)
        
        if not char:
            await query.answer("Character not found!")
            return CHOOSING_PERSONA
        
        if char["is_locked"]:
            # Show unlock options
            keyboard = stars_payment_manager.create_unlock_keyboard(
                character_id, char["name"], char["price_stars"]
            )
            
            # Get AI model benefits
            ai_benefits = ai_model_manager.get_character_tier_benefits(char["price_stars"])
            
            await query.edit_message_text(
                f"🔒 **Unlock {char['name']}**\n\n"
                f"💫 Price: {char['price_stars']} Stars\n"
                f"🎭 Role: {char['role']}\n"
                f"📍 Region: {char['region']}\n"
                f"💬 Language: {char['language']}\n"
                f"🤖 {ai_benefits}\n\n"
                f"📝 {char['description']}\n\n"
                f"Click below to unlock with Telegram Stars!",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        return CHOOSING_PERSONA
    
    elif data.startswith("pay_stars:"):
        character_id = data.split(":")[1]
        char = character_manager.get_character_by_id(character_id)
        
        if not char or not char["is_locked"]:
            await query.answer("Character not available for purchase!")
            return CHOOSING_PERSONA
        
        # Create Stars invoice
        invoice_data = stars_payment_manager.create_stars_invoice(
            user_id, character_id, char["name"], char["price_stars"]
        )
        
        if invoice_data:
            try:
                await context.bot.send_invoice(
                    chat_id=user_id,
                    **invoice_data
                )
                await query.edit_message_text(
                    f"💫 **Payment Invoice Sent!**\n\n"
                    f"Check your Telegram for the payment invoice to unlock {char['name']}.\n\n"
                    f"After payment, you'll be able to chat with her! 😘"
                )
            except Exception as e:
                logger.error(f"Error sending invoice: {e}")
                await query.edit_message_text(
                    "❌ Error creating payment invoice. Please try again later."
                )
        else:
            await query.edit_message_text(
                "❌ Error creating payment invoice. Please try again later."
            )
        return CHOOSING_PERSONA
    
    elif data == "cancel_unlock":
        await show_characters(update, context)
        return CHOOSING_PERSONA
    
    return CHOOSING_PERSONA

async def characters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /characters command"""
    await show_characters(update, context)
    return CHOOSING_PERSONA

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    logger.info(f"Chat message received from user {user_id}: {msg[:50]}...")
    
    # Check if user has paid (check both systems for compatibility)
    is_paid = is_user_paid(user_id) or is_user_paid_upi(user_id)
    
    # Debug logging
    message_count = get_user_message_count(user_id)
    logger.info(f"DEBUG: User {user_id} - Messages: {message_count}, Paid: {is_paid}")
    
    # Check if user has paid
    if is_paid:
        # Paid user - unlimited messages
        logger.info(f"User {user_id} is paid, processing message")
        save_message(user_id, msg, is_user=1)
        
        # Get character-specific prompt and price
        character_prompt = character_manager.get_character_prompt(user_id)
        active_char = character_manager.get_active_character(user_id)
        character_price = active_char["price_stars"] if active_char else 0
        
        prompt = build_prompt(user_id, character_prompt)
        reply = get_llm_reply(prompt, character_price)
        save_message(user_id, reply, is_user=0)
        await update.message.reply_text(reply)
        return CHATTING
    
    # Free user - check message limit
    if message_count >= FREE_MESSAGE_LIMIT:
        # User has reached free message limit - show Stars payment option
        logger.info(f"User {user_id} reached message limit, showing Stars payment")
        
        # Create Stars payment keyboard for unlimited access
        keyboard = stars_payment_manager.create_unlimited_access_keyboard()
        
        await update.message.reply_text(
            f"💋 I'm loving our chat, but I need you to unlock me for more! You've used {message_count} free messages.\n\n"
            f"🌟 **Unlock Unlimited Access**\n"
            f"• Chat with any character unlimited times\n"
            f"• Access to all premium AI models\n"
            f"• No more message restrictions\n\n"
            f"Click below to unlock with Telegram Stars! 😘",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CHATTING
    
    # Free user within limit - process the message
    logger.info(f"User {user_id} processing message {message_count + 1}/{FREE_MESSAGE_LIMIT}")
    save_message(user_id, msg, is_user=1)
    
    # Get character-specific prompt and price
    character_prompt = character_manager.get_character_prompt(user_id)
    active_char = character_manager.get_active_character(user_id)
    character_price = active_char["price_stars"] if active_char else 0
    
    prompt = build_prompt(user_id, character_prompt)
    reply = get_llm_reply(prompt, character_price)
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
    """Show payment options for unlimited access"""
    user_id = update.effective_user.id
    logger.info(f"Pay command received from user {user_id}")
    
    # Check if user has paid
    is_paid = is_user_paid(user_id) or is_user_paid_upi(user_id)
    
    if is_paid:
        await update.message.reply_text("💋 You're already unlocked! Enjoy unlimited access to me! 😘")
        return CHATTING
    
    message_count = get_user_message_count(user_id)
    
    # Create Stars payment keyboard for unlimited access
    keyboard = stars_payment_manager.create_unlimited_access_keyboard()
    
    await update.message.reply_text(
        f"💋 I'm loving our chat, but I need you to unlock me for more! You've used {message_count} free messages.\n\n"
        f"🌟 **Unlock Unlimited Access**\n"
        f"• Chat with any character unlimited times\n"
        f"• Access to all premium AI models\n"
        f"• No more message restrictions\n\n"
        f"Click below to unlock with Telegram Stars! 😘",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    return CHATTING



async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout for Stars payments (digital goods)"""
    query = update.pre_checkout_query
    user_id = query.from_user.id
    
    logger.info(f"Pre-checkout received from user {user_id}")
    
    # Validate the pre-checkout query
    if stars_payment_manager.validate_pre_checkout(query):
        # Approve the order
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user_id}")
    else:
        # Reject the order with error message
        await query.answer(
            ok=False, 
            error_message="Sorry, we couldn't process your order. Please try again or contact support."
        )
        logger.warning(f"Pre-checkout rejected for user {user_id}")

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful Telegram Stars payments"""
    payment_data = update.message.successful_payment
    user_id = update.effective_user.id
    
    logger.info(f"Payment received from user {user_id}: {payment_data}")
    
    # Parse payload to determine payment type
    payload_parts = payment_data.invoice_payload.split(":")
    payment_type = payload_parts[0]
    
    if payment_type == "character_unlock":
        # Handle character unlock payment
        character_id = int(payload_parts[1])
        char = character_manager.get_character_by_id(character_id)
        
        if char:
            # Record transaction
            stars_payment_manager.record_transaction(
                user_id, character_id, char["price_stars"], 
                payment_data.total_amount, payment_data.telegram_payment_charge_id
            )
            
            # Unlock character for the user
            if character_manager.unlock_character(user_id, character_id):
                # Get AI model benefits
                ai_benefits = ai_model_manager.get_character_tier_benefits(char["price_stars"])
                
                await update.message.reply_text(
                    f"🎉 **Payment Successful!**\n\n"
                    f"You've unlocked **{char['name']}**!\n\n"
                    f"💫 Amount: {payment_data.total_amount} Stars\n"
                    f"🎭 Character: {char['name']} ({char['role']})\n"
                    f"🤖 {ai_benefits}\n\n"
                    f"Send /characters to select her and start chatting! 😘\n\n"
                    f"💡 **Support**: If you have any issues, send /support",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Error unlocking character. Please contact support with /support"
                )
        else:
            await update.message.reply_text(
                "❌ Character not found. Please contact support with /support"
            )
    
    elif payment_type == "unlimited_access":
        # Handle unlimited access payment
        stars_amount = int(payload_parts[1])
        
        # Mark user as paid for unlimited access
        mark_user_paid(user_id)
        
        # Record transaction
        stars_payment_manager.record_unlimited_access_transaction(
            user_id, stars_amount, payment_data.total_amount, 
            payment_data.telegram_payment_charge_id
        )
        
        await update.message.reply_text(
            f"🎉 **Unlimited Access Unlocked!**\n\n"
            f"🌟 **Welcome to Premium!**\n\n"
            f"💫 Amount: {payment_data.total_amount} Stars\n"
            f"✨ **What you get:**\n"
            f"• Unlimited messages with any character\n"
            f"• Access to all premium AI models\n"
            f"• No more message restrictions\n"
            f"• Priority support\n\n"
            f"Send /characters to explore all characters! 😘\n\n"
            f"💡 **Support**: If you have any issues, send /support",
            parse_mode='Markdown'
        )
    
    else:
        await update.message.reply_text(
            "❌ Unknown payment type. Please contact support with /support"
        )

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /support command for customer support"""
    await update.message.reply_text(
        "🆘 **Customer Support**\n\n"
        "If you have any issues with:\n"
        "• Character unlocks\n"
        "• Payment problems\n"
        "• Chat functionality\n"
        "• Technical issues\n\n"
        "Please contact our support team:\n"
        "📧 Email: support@yourbot.com\n"
        "💬 Telegram: @yoursupportbot\n\n"
        "Include your payment ID if reporting payment issues.",
        parse_mode='Markdown'
    )

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /terms command for Terms and Conditions"""
    await update.message.reply_text(
        "📋 **Terms and Conditions**\n\n"
        "**Digital Services Terms**\n\n"
        "1. **Service Description**: This bot provides AI chat services with virtual characters\n"
        "2. **Payment**: All payments are processed through Telegram Stars\n"
        "3. **Refunds**: Digital services are non-refundable once delivered\n"
        "4. **Usage**: Service is for personal entertainment only\n"
        "5. **Privacy**: We respect your privacy and don't store personal data\n\n"
        "**By using this service, you agree to these terms.**\n\n"
        "For full terms, visit: https://yourbot.com/terms",
        parse_mode='Markdown'
    )

def main():
    logger.info("Starting bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_PERSONA: [
                CommandHandler("characters", characters_command),
                CallbackQueryHandler(handle_character_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
            ],
            CHATTING: [
                CommandHandler("characters", characters_command),
                CommandHandler("pay", pay),
                CallbackQueryHandler(handle_character_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    
    app.add_handler(conv_handler)
    
    # Add payment handlers (outside conversation handler)
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    
    # Add support and terms commands (available in all states)
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("terms", terms_command))
    
    logger.info("Bot started successfully!")
    app.run_polling()

if __name__ == '__main__':
    main()
