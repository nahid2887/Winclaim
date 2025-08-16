import openai
import os
from dotenv import load_dotenv
from Chat.internalchatengine import Message  # keep using the Message class

load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

def convert_to_internal_format(messages_queryset):
    return [
        Message(
            id=str(msg.id),
            sender=msg.sender,
            content=msg.content,
            flagged=msg.flagged,
            flag_type=msg.flag_type or None
        )
        for msg in messages_queryset
    ]

def stream_gpt_response(user_input, history_queryset):
    history = convert_to_internal_format(history_queryset)

    messages = [
        {"role": "system", "content": "You are an assistant that helps users write professional, clear responses to insurance adjusters."}
    ]
    for msg in history:
        role = "user" if msg.sender == "User" else "assistant"
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": user_input})

    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    stream = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
        stream=True
    )
    
    # Convert new API format to old format for backward compatibility
    for chunk in stream:
        if chunk.choices and hasattr(chunk.choices[0], "delta") and chunk.choices[0].delta.content:
            # Convert to old API format
            yield {
                "choices": [{
                    "delta": {
                        "content": chunk.choices[0].delta.content
                    }
                }]
            }



