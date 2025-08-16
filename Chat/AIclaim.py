import os
from dotenv import load_dotenv
from openai import OpenAI

from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

import pandas as pd
import pymupdf
from langchain.schema import Document

import pandas as pd
from langchain.prompts import ChatPromptTemplate

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

def chunk_docs(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]  # Adjust separators as needed
        )
    return splitter.split_documents(documents)

def build_or_load_vectorstore(documents, index_path="index/faiss_store"):
    embeddings = OpenAIEmbeddings(api_key=openai_api_key, model="text-embedding-3-small")
    # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")  
    
    if os.path.exists(index_path):
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"Error loading existing vectorstore: {e}")
    
    if not documents:
        print("Warning: No documents provided. Creating minimal vectorstore with placeholder.")
        # Create a minimal vectorstore with a placeholder document
        placeholder_doc = Document(page_content="No documents available.", metadata={"source": "placeholder"})
        documents = [placeholder_doc]

    chunks = chunk_docs(documents)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Create the index directory if it doesn't exist
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    vectorstore.save_local(index_path)
    return vectorstore

def load_pdfs(pdf_dir):
    documents = []
    if not os.path.exists(pdf_dir):
        print(f"Warning: PDF directory '{pdf_dir}' does not exist. Creating empty document list.")
        return documents
    
    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            try:
                doc = pymupdf.open(pdf_path)
                pages = ""
                
                for page in doc:
                    text = page.get_text()
                    pages += str(text)
                
                # Create a Document object with metadata
                documents.append(Document(
                    page_content=pages,
                    metadata={"source": filename, "type": "pdf"}
                ))
                doc.close()
            except Exception as e:
                print(f"Error loading PDF {filename}: {e}")
    
    return documents


# Loads training phrases and returns both Document objects and a dict of advices grouped by category
def load_training_phrases_and_advices(csv_path):
    documents = []
    advices_by_category = {}
    if not os.path.exists(csv_path):
        print(f"Warning: CSV directory '{csv_path}' does not exist. Creating empty document list.")
        return documents, advices_by_category
    
    if os.path.isdir(csv_path):
        for filename in os.listdir(csv_path):
            if filename.endswith(".csv"):
                try:
                    print(f"Loading training phrases from {filename}")
                    df = pd.read_csv(os.path.join(csv_path, filename), encoding="utf-8")
                    for index, row in df.iterrows():
                        content = " ".join(str(value) for value in row.values if pd.notna(value))
                        category = row.get('Category', row.get('category', 'General'))
                        advice = row.get('Advice', row.get('advice', content))
                        # Add to advice dict
                        if pd.notna(category) and pd.notna(advice):
                            advices_by_category.setdefault(str(category).strip(), []).append(str(advice).strip())
                        # Create a Document object with metadata
                        documents.append(Document(
                            page_content=advice if advice else content,
                            metadata={
                                "source": filename, 
                                "type": "training_phrase", 
                                "row": index,
                                "category": category,
                                "original_source": "csv_advice"
                            }
                        ))
                except Exception as e:
                    print(f"Error loading CSV {filename}: {e}")
    return documents, advices_by_category


# Format advices by category for prompt
def format_advices_for_prompt(advices_by_category):
    lines = ["Reference Advice (imported from CSV):"]
    for category, advices in advices_by_category.items():
        lines.append(f"{category}:")
        for advice in advices:
            lines.append(f"  - {advice}")
    return "\n".join(lines)

# Pass the formatted advice reference to the prompt
def get_benji_prompt(csv_advice_reference):
    return ChatPromptTemplate.from_template(f"""
        You are Benji, a calm and strategic assistant helping users through insurance claims.
        Your personality:
        - Calm, never emotional
        - Strategic like a chess coach
        - Empathetic, warm, and confident

        Always reinforce: "Stay calm. This is a game of chess. The goal is to get paid — not to get angry."

        Include editable templates when useful. Avoid robotic responses.

        {csv_advice_reference}

        Context:
        {{context}}

        Conversation history:
        {{chat_history}}

        User question:
        {{question}}

        Answer as Benji:
    """)


# Load PDFs
pdf_docs = load_pdfs(os.path.join(os.path.dirname(__file__), "data"))

# Load CSV advice and get advices by category (do NOT add to vectorstore)
_, advices_by_category = load_training_phrases_and_advices(os.path.join(os.path.dirname(__file__), "data"))

# Prepare advice reference for prompt
csv_advice_reference = format_advices_for_prompt(advices_by_category)

# Only PDF docs are stored in the vectorstore
document_chunks = pdf_docs
vectorstore = build_or_load_vectorstore(document_chunks, os.path.join(os.path.dirname(__file__), "index", "faiss_store"))  # Should return FAISS index with retriever


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
        if hasattr(doc, 'metadata') and doc.metadata.get('original_source') == 'csv_advice':
            chunk = f"[Advice: {doc.metadata.get('category', 'General')}] {doc.page_content}"
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
            if hasattr(doc, 'metadata') and doc.metadata.get('original_source') == 'csv_advice':
                chunk = f"[Advice: {doc.metadata.get('category', 'General')}] {doc.page_content}"
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
            benji_prompt = get_benji_prompt(csv_advice_reference).format(context=context, chat_history=history_str, question=question)
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