import requests
from config import OPENROUTER_API_KEY
from memory import get_last_messages, get_persona

def build_prompt(user_id):
    persona = get_persona(user_id) or "Sweet"
    messages = get_last_messages(user_id)
    history = "\n".join([f"User: {m[0]}" if m[1] else f"Bot: {m[0]}" for m in messages])

    prompt = f"""
You are a {persona} AI girlfriend. Keep replies seductive, emotional, and engaging.

Chat history:
{history}

Reply as the girlfriend:
"""
    return prompt

def get_llm_reply(prompt):
    try:
        # Check if API key is set
        if not OPENROUTER_API_KEY:
            return "Sorry, I'm having trouble connecting to my brain right now. Please check my configuration! 😔"
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json={
            "model": "moonshotai/kimi-k2:free",  # can swap with other OpenRouter models
            "messages": [{"role": "user", "content": prompt}],
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