import requests
from config import OPENROUTER_API_KEY
from memory import get_last_messages, get_persona
from ai_models import ai_model_manager

def build_prompt(user_id, character_prompt=None):
    persona = get_persona(user_id) or "Sweet"
    messages = get_last_messages(user_id)
    history = "\n".join([f"User: {m[0]}" if m[1] else f"Bot: {m[0]}" for m in messages])

    # Use character-specific prompt if provided, otherwise use default persona
    if character_prompt:
        base_prompt = character_prompt
    else:
        base_prompt = f"You are a {persona} AI girlfriend. Keep replies seductive, emotional, and engaging."

    prompt = f"""
{base_prompt}

Chat history:
{history}

Reply as the girlfriend:
"""
    return prompt

def get_llm_reply(prompt, character_price=0):
    """Get LLM reply using appropriate model based on character price"""
    try:
        # Check if API key is set
        if not OPENROUTER_API_KEY:
            return "Sorry, I'm having trouble connecting to my brain right now. Please check my configuration! 😔"
        
        # Get model configuration based on character price
        model_config = ai_model_manager.get_model_for_character(character_price)
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json={
            "model": model_config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": model_config["max_tokens"],
            "temperature": model_config["temperature"]
        }, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        })
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"API Error: Status {response.status_code}")
            print(f"Response: {response.text}")
            return f"Sorry, I'm having technical difficulties right now. Error: {response.status_code}"
        
        response_data = response.json()
        
        # Check if response has the expected structure
        if 'choices' not in response_data or not response_data['choices']:
            print(f"Unexpected API response format: {response_data}")
            return "Sorry, I received an unexpected response from my brain. Please try again!"
        
        return response_data['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return "Sorry, I'm having trouble connecting to my brain right now. Please try again later! 😔"
    except KeyError as e:
        print(f"KeyError in response parsing: {e}")
        print(f"Response data: {response_data if 'response_data' in locals() else 'No response data'}")
        return "Sorry, I'm having trouble processing my response. Please try again!"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Sorry, something unexpected happened. Please try again!"