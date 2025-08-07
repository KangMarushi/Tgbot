Create a Telegram chatbot named "SextBot" that acts as an AI girlfriend. The bot should have the following features for the MVP:

1. Telegram Integration:
  - On `/start`, welcome the user with a flirty message.
  - Ask them to select a girlfriend persona: "Sweet", "Flirty", "Dominant", or "Submissive".
  - Store the user's name, persona choice, and basic metadata.

2. Chat System:
  - Connect to an open-source LLM (like Mistral 7B or Mixtral via OpenRouter API or LM Studio locally).
  - Build a prompt template that includes the persona type and recent chat memory (last 10 messages).
  - Return responses from the LLM back to the user via Telegram.

3. Memory & Context:
  - Use SQLite or Redis to store:
    - User profiles (Telegram ID, name, chosen persona)
    - Chat history (recent 10 messages)
    - Subscription status

4. Monetization:
  - Users get 10 free messages.
  - After that, prompt them to pay via Razorpay or Stripe to unlock more chat.
  - Payment plans: ₹9/day or ₹49/week.
  - Integrate payment gateway and verify success via webhook or polling.
  - On successful payment, unlock unlimited messages for the duration.

5. Hosting:
  - Make the code compatible for deployment on Railway or Render.
  - Include `.env` for API keys (Telegram Bot Token, OpenRouter API Key, Razorpay credentials).

6. Code Structure:
  - `bot.py`: Telegram bot logic
  - `chat_engine.py`: Prompt handling and LLM response
  - `memory.py`: Chat history and profile persistence
  - `payment.py`: Razorpay or Stripe payment logic
  - `config.env`: Secrets

7. Compliance:
  - Keep replies seductive but avoid nudity, explicit pornographic terms, or anything against Telegram or Google Play policy.
  - Add a `/help` and `/privacy` command that links to basic guidelines and app usage terms.

Create this as a full working Python project using `python-telegram-bot` library and requests for APIs.
