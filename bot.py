import logging
from telegram import Update, ReplyKeyboardMarkup, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from config import TELEGRAM_BOT_TOKEN
from memory import save_user, save_message, get_persona, get_user_message_count, is_user_paid, mark_user_paid
from chat_engine import build_prompt, get_llm_reply
from payment import create_payment_instructions, verify_payment_screenshot, is_user_paid_upi, get_qr_image_bytes
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from user {update.effective_user.id}")
    
    # Check if user has an active character
    active_char = character_manager.get_active_character(update.effective_user.id)
    
    if active_char:
        # User already has an active character, go directly to chat
        await update.message.reply_text(
            f"Welcome back! You're chatting with {active_char['name']} 😘\n\n"
            f"Send /characters to change your AI girlfriend or just start chatting!"
        )
        return CHATTING
    else:
        # New user or no active character, show character selection
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
    
    # Check message count for free users BEFORE processing
    message_count = get_user_message_count(user_id)
    
    if message_count >= FREE_MESSAGE_LIMIT:
        # User has exceeded free limit - don't process the message
        logger.info(f"User {user_id} exceeded limit ({message_count}/{FREE_MESSAGE_LIMIT})")
        payment_info = create_payment_instructions(user_id)
        await update.message.reply_text(
            f"💋 I'm loving our chat, but I need you to unlock me for more! "
            f"You've used {message_count} free messages.\n\n"
            f"To unlock unlimited access, pay ₹{payment_info['amount']} to:\n"
            f"💳 {payment_info['upi_id']}\n\n"
            f"After payment, send me a screenshot of the transaction! 😘"
        )
        
        # Try to send QR code image, but don't fail if it doesn't work
        try:
            import os
            from io import BytesIO
            
            # Try to get QR image as bytes
            qr_bytes = get_qr_image_bytes()
            if qr_bytes:
                logger.info(f"QR image created, size: {len(qr_bytes)} bytes")
                await update.message.reply_photo(
                    photo=BytesIO(qr_bytes),
                    caption="📸 Scan this QR code to pay, then send me the screenshot!"
                )
                logger.info("QR code sent successfully")
            else:
                logger.warning("Failed to create QR image bytes")
                await update.message.reply_text(
                    "📸 Please scan the QR code from your UPI app or pay manually using the UPI ID above!"
                )
        except Exception as e:
            logger.warning(f"Failed to send QR code image: {e}")
            await update.message.reply_text(
                "📸 Please scan the QR code from your UPI app or pay manually using the UPI ID above!"
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
    user_id = update.effective_user.id
    logger.info(f"Pay command received from user {user_id}")
    
    # Check if user has paid (check both systems for compatibility)
    is_paid = is_user_paid(user_id) or is_user_paid_upi(user_id)
    
    if is_paid:
        await update.message.reply_text("💋 You're already unlocked! Enjoy unlimited access to me! 😘")
        return CHATTING
    
    payment_info = create_payment_instructions(user_id)
    message_count = get_user_message_count(user_id)
    
    await update.message.reply_text(
        f"💋 Unlock unlimited access to me!\n\n"
        f"You've used {message_count}/{FREE_MESSAGE_LIMIT} free messages.\n\n"
        f"To unlock, pay ₹{payment_info['amount']} to:\n"
        f"💳 {payment_info['upi_id']}\n\n"
        f"After payment, send me a screenshot of the transaction! 😘"
    )
    
    # Try to send QR code image, but don't fail if it doesn't work
    try:
        import os
        from io import BytesIO
        
        # Try to get QR image as bytes
        qr_bytes = get_qr_image_bytes()
        if qr_bytes:
            logger.info(f"QR image created, size: {len(qr_bytes)} bytes")
            await update.message.reply_photo(
                photo=BytesIO(qr_bytes),
                caption="📸 Scan this QR code to pay, then send me the screenshot!"
            )
            logger.info("QR code sent successfully")
        else:
            logger.warning("Failed to create QR image bytes")
            await update.message.reply_text(
                "📸 Please scan the QR code from your UPI app or pay manually using the UPI ID above!"
            )
    except Exception as e:
        logger.warning(f"Failed to send QR code image: {e}")
        await update.message.reply_text(
            "📸 Please scan the QR code from your UPI app or pay manually using the UPI ID above!"
        )
    
    return CHATTING

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment screenshot verification"""
    user_id = update.effective_user.id
    logger.info(f"Payment screenshot received from user {user_id}")
    
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        image_bytes = await file.download_as_bytearray()
        
        if verify_payment_screenshot(image_bytes, user_id):
            # Mark user as paid in the main database as well
            mark_user_paid(user_id)
            await update.message.reply_text(
                "✅ Payment verified! You now have unlimited access to your AI girlfriend! 😘"
            )
        else:
            await update.message.reply_text(
                "❌ Couldn't verify your payment. Please make sure:\n"
                "• The UPI ID and amount are clearly visible\n"
                "• You paid the correct amount\n"
                "• The screenshot shows the transaction details\n\n"
                "Try again or contact support if you're sure you paid correctly."
            )
    except Exception as e:
        logger.error(f"Error processing payment screenshot: {e}")
        await update.message.reply_text(
            "❌ Error processing your screenshot. Please try again or contact support."
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

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful Stars payment for digital goods"""
    payment_info = update.message.successful_payment
    user_id = update.effective_user.id
    
    logger.info(f"Successful payment received from user {user_id}")
    
    # Process the successful payment
    payment_data = stars_payment_manager.process_successful_payment(payment_info)
    
    if payment_data["success"]:
        character_id = payment_data["character_id"]
        char = character_manager.get_character_by_id(character_id)
        
        if char:
            # Record transaction in database
            stars_payment_manager.record_transaction(
                user_id, character_id, char["price_stars"], 
                payment_data["telegram_payment_charge_id"]
            )
            
            # Unlock character for the user
            if character_manager.unlock_character(user_id, character_id):
                # Get AI model benefits
                ai_benefits = ai_model_manager.get_character_tier_benefits(char["price_stars"])
                
                await update.message.reply_text(
                    f"🎉 **Payment Successful!**\n\n"
                    f"You've unlocked **{char['name']}**!\n\n"
                    f"💫 Amount: {payment_data['total_amount']} Stars\n"
                    f"🎭 Character: {char['name']} ({char['role']})\n"
                    f"🤖 {ai_benefits}\n\n"
                    f"Send /characters to select her and start chatting! 😘\n\n"
                    f"💡 **Support**: If you have any issues, send /support",
                    parse_mode='Markdown'
                )
                logger.info(f"Character {character_id} unlocked for user {user_id}")
            else:
                await update.message.reply_text(
                    "❌ Error unlocking character. Please contact support with your payment ID."
                )
                logger.error(f"Failed to unlock character {character_id} for user {user_id}")
        else:
            await update.message.reply_text(
                "❌ Character not found. Please contact support with your payment ID."
            )
            logger.error(f"Character {character_id} not found for user {user_id}")
    else:
        await update.message.reply_text(
            "❌ Payment processing error. Please contact support with your payment ID."
        )
        logger.error(f"Payment processing error for user {user_id}: {payment_data.get('error', 'Unknown error')}")

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
                MessageHandler(filters.PHOTO, handle_payment_screenshot),
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
