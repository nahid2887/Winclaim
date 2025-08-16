
import os
from dotenv import load_dotenv
from openai import OpenAI
from utils.loaders import load_pdfs, load_training_phrases
from utils.embedder import build_or_load_vectorstore
from utils.prompts import get_benji_prompt

load_dotenv()
openai_api_key = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# Global system prompt
SYSTEM_PROMPT = (
    "You are Benji, a calm and strategic assistant trained to guide users through insurance claims like a chess game. "
    "Your goal is to help them get paid, not to get angry."
)

# Shared history starter
initial_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# Vectorstore init

# Load PDFs
pdf_docs = load_pdfs("data/")

# Load CSV advice and tag with metadata
raw_training_docs = load_training_phrases("data/")
training_docs = []
for doc in raw_training_docs:
    # Access Document attributes robustly
    advice_text = getattr(doc, 'Advice', getattr(doc, 'advice', ''))
    category = getattr(doc, 'Category', getattr(doc, 'category', 'General'))
    training_docs.append({
        'page_content': advice_text,
        'category': category,
        'source': 'csv_advice'
    })

# Merge all document chunks
document_chunks = pdf_docs + training_docs
vectorstore = build_or_load_vectorstore(document_chunks)  # Should return FAISS index with retriever


def create_session_history():
    return initial_history.copy()


def retrieve_context(question: str, top_k: int = 4):
    """
    Use FAISS retriever to get relevant document chunks, with robust formatting for CSV advice.
    """
    # Retrieve top 4 chunks, do not truncate
    docs = vectorstore.similarity_search(question, k=4)
    formatted_chunks = []
    for doc in docs:
        # If advice is from CSV, show category and tag
        if hasattr(doc, 'source') and doc.source == 'csv_advice':
            chunk = f"[Advice: {getattr(doc, 'category', 'General')}] {doc.page_content}"
        elif isinstance(doc, dict) and doc.get('source') == 'csv_advice':
            chunk = f"[Advice: {doc.get('category', 'General')}] {doc.get('page_content', '')}"
        else:
            chunk = doc.page_content
        formatted_chunks.append(chunk)
    return "\n\n".join(formatted_chunks)


def get_benji_response(question, chat_history):
    import traceback
    try:
        # Retrieve relevant knowledge
        # Get all context chunks as a list
        docs = vectorstore.similarity_search(question, k=4)
        context_chunks = []
        for doc in docs:
            if hasattr(doc, 'source') and doc.source == 'csv_advice':
                chunk = f"[Advice: {getattr(doc, 'category', 'General')}] {doc.page_content}"
            elif isinstance(doc, dict) and doc.get('source') == 'csv_advice':
                chunk = f"[Advice: {doc.get('category', 'General')}] {doc.get('page_content', '')}"
            else:
                chunk = doc.page_content
            context_chunks.append(chunk)

        def estimate_tokens(text):
            # Rough estimate: 1 token ≈ 4 characters
            return len(text) // 4

        max_tokens = 8000  # Safe threshold for GPT-4 (adjust as needed)
        history = chat_history.copy()
        # Try to keep as much history and context as possible
        while True:
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history])
            context = "\n\n".join(context_chunks)
            benji_prompt = get_benji_prompt().format(context=context, chat_history=history_str, question=question)
            total_text = benji_prompt + question + history_str + context
            total_tokens = estimate_tokens(total_text)
            if total_tokens < max_tokens:
                break
            # First, trim history (after system prompt)
            if len(history) > 1:
                history.pop(1)
            # If history is minimal, trim context chunks
            elif len(context_chunks) > 1:
                context_chunks.pop(0)
            else:
                break
        messages = history.copy()
        messages.append({"role": "system", "content": benji_prompt})
        messages.append({"role": "user", "content": question})
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.1
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply, messages
    except Exception as e:
        tb = traceback.format_exc()
        error_type = type(e).__name__
        return f"Error ({error_type}): {str(e)}\nTraceback:\n{tb}", chat_history

if __name__ == "__main__":
    print("Welcome to Benji! Type 'exit' to quit.")
    chat_history = create_session_history()
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        reply, chat_history = get_benji_response(user_input, chat_history)
        if reply.startswith("Error:"):
            print(f"Benji: {reply} (Check your API key, vectorstore, or data files)")
        else:
            print(f"Benji: {reply}\n")