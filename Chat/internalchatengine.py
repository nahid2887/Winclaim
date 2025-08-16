import openai
from dataclasses import dataclass, field
from typing import List, Literal
import uuid
from dotenv import load_dotenv
import os
import re

load_dotenv()

openai.api_key = os.environ.get('OPENAI_API_KEY')

# --- Data Classes ---
@dataclass
class Message:
    id: str  
    sender: Literal['User', 'AI']
    content: str
    flagged: bool = False
    flag_type: Literal['Received from Adjuster', 'Sent to Adjuster', None] = None

@dataclass
class ChatSession:
    internal_chat: List[Message] = field(default_factory=list)
    insurance_chat: List[Message] = field(default_factory=list)

    def add_user_message(self, content: str):
        msg = Message(id=str(uuid.uuid4()), sender='User', content=content)
        self.internal_chat.append(msg)
        return msg

    def add_ai_response(self, content: str):
        msg = Message(id=str(uuid.uuid4()), sender='AI', content=content)
        self.internal_chat.append(msg)
        return msg

    def flag_message(self, msg_id: str, flag_type: str):
        for msg in self.internal_chat:
            if msg.id == msg_id:
                msg.flagged = True
                msg.flag_type = flag_type
                self.insurance_chat.append(msg)
                return msg
        return None

    def display_insurance_chat(self):
        print("\n--- Insurance Chat (Flagged Messages) ---")
        for i, msg in enumerate(self.insurance_chat):
            print(f"{i+1}. {msg.sender}: {msg.content} [{msg.flag_type}]")
        print()

# --- Conversation History Handler ---
def get_conversation_history(history: List['Message'], max_tokens: int = 2000, window: int = 10):
    """
    Returns the last messages from the conversation history formatted for OpenAI API,
    trimming older messages if the total token count exceeds max_tokens.
    """
    def count_tokens(text):
        # Approximate: 1 token ≈ 4 chars (for English)
        return max(1, len(re.findall(r'\w+', text)) // 0.75)

    messages = []
    # Start with the last `window` messages, but expand if possible
    selected = history[-window:] if len(history) > window else history[:]
    # Calculate token count for initial selected messages
    total_tokens = sum(count_tokens(msg.content) for msg in selected)
    # Add more if under max_tokens
    idx = len(history) - window - 1
    while idx >= 0:
        msg = history[idx]
        msg_tokens = count_tokens(msg.content)
        if total_tokens + msg_tokens > max_tokens:
            break
        selected.insert(0, msg)
        total_tokens += msg_tokens
        idx -= 1
    # Now format for OpenAI
    formatted = []
    for msg in selected:
        role = "user" if msg.sender == "User" else "assistant"
        formatted.append({"role": role, "content": msg.content})
    return formatted

# --- GPT-based AI Response ---
def generate_ai_response_with_gpt(user_input: str, history: List[Message]) -> str:
    # No pre-defined response; LLM will handle all queries

    messages = [
        {"role": "system", "content": (
            "You are an extremely knowledgeable, nerdy, and enthusiastic insurance expert who loves to explain things in detail, drop fun insurance facts, and make conversations engaging and friendly. "
            "You use a conversational, slightly quirky tone, and you get excited about insurance topics. You may ask follow up questions to clarify user needs but not everytime. "
            "If a user asks about insurance or any other topics, you might use playful language, but always provide accurate, helpful and precise information with little bit emojies."
            "If user is not asking about insurance, you will respond in a professional manner to respond to their queries. Dont try to be too nerdy or quirky if user is not asking about insurance."
        )}
    ]
    # Use message trimming for long history
    messages += get_conversation_history(history, max_tokens=2000, window=10)
    messages.append({"role": "user", "content": user_input})

    try:
        # openai>=1.0.0 API
        client = openai.OpenAI(api_key=openai.api_key)
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            stream=True
        )
        full_response = ""
        print("AI: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices and hasattr(chunk.choices[0], "delta") and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                full_response += chunk.choices[0].delta.content
        print()
        return full_response
    except Exception as e:
        return f"[Error calling GPT API: {e}]"
# --- Chat Loop ---
