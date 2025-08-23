from dotenv import load_dotenv
load_dotenv()
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
import os
import pymupdf
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
import json

# Django imports for database access
try:
    import django
    from django.conf import settings
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'claim.settings')
        django.setup()
    from Chat.models import UserClaimUpload
    from accounts.models import CustomUser
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    print("Django not available - using fallback mode")


def get_user_claim_info(user, upload_id=None):
    """
    Get user claim information from database
    Args:
        user: Django User object or user_id string
        upload_id: Optional specific upload ID, if None gets most recent
    Returns:
        Dictionary with claim info and user details
    """
    if not DJANGO_AVAILABLE:
        return get_default_claim_info()
    
    try:
        # Handle user parameter
        if isinstance(user, str):
            user_obj = CustomUser.objects.get(user_id=user)
        else:
            user_obj = user
            
        # Get claim upload
        if upload_id:
            claim_upload = UserClaimUpload.objects.get(
                upload_id=upload_id, 
                user=user_obj, 
                is_active=True
            )
        else:
            claim_upload = UserClaimUpload.objects.filter(
                user=user_obj, 
                is_active=True
            ).order_by('-updated_at').first()
        
        if not claim_upload:
            return get_default_claim_info(user_obj)
        
        # Extract claim information
        claim_info = claim_upload.get_claim_info_dict()
        
        return {
            'insurance_company': claim_info.get('insurance_company_name', 'Not provided'),
            'policy_number': claim_info.get('policy_number', 'Not provided'),
            'policy_report_number': claim_info.get('police_report_number', 'Not provided'),
            'adjuster_name': claim_info.get('adjuster_name', 'Not provided'),
            'adjuster_phone': claim_info.get('adjuster_phone_number', 'Not provided'),
            'claim_number': claim_info.get('add_claim_number', 'Not provided'),
            'adjuster_email': claim_info.get('adjuster_email', 'Not provided'),
            'user_full_name': user_obj.full_name or 'Not provided',
            'email_address': user_obj.email or 'Not provided',
            'user_phone_no': user_obj.phone_number or 'Not provided',
            'upload_folder_path': claim_upload.upload_folder_path,
            'local_folder_name': f"user_{user_obj.user_id}_{str(claim_upload.upload_id)[:8]}",
            'upload_id': str(claim_upload.upload_id)
        }
        
    except Exception as e:
        print(f"Error getting user claim info: {e}")
        return get_default_claim_info()


def get_default_claim_info(user_obj=None):
    """Fallback claim info when database is not available"""
    return {
        'insurance_company': 'Not provided',
        'policy_number': 'Not provided', 
        'policy_report_number': 'Not provided',
        'adjuster_name': 'Not provided',
        'adjuster_phone': 'Not provided',
        'claim_number': 'Not provided',
        'adjuster_email': 'Not provided',
        'user_full_name': user_obj.full_name if user_obj else 'Not provided',
        'email_address': user_obj.email if user_obj else 'Not provided',
        'user_phone_no': user_obj.phone_number if user_obj else 'Not provided',
        'upload_folder_path': 'data/',
        'local_folder_name': 'default_local_knowledge',
        'upload_id': None
    }

# Load PDF documents from a directory
def load_pdfs(pdf_path_or_dir):
    print(pdf_path_or_dir)
    documents = []
    if os.path.isdir(pdf_path_or_dir):
        for filename in os.listdir(pdf_path_or_dir):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(pdf_path_or_dir, filename)
                doc = pymupdf.open(pdf_path)
                pages = ""
                for page in doc:
                    text = page.get_text()
                    pages += str(text)
                documents.append(Document(
                    page_content=pages,
                    metadata={"source": filename, "type": "pdf"}
                ))
                doc.close()
    elif os.path.isfile(pdf_path_or_dir) and pdf_path_or_dir.endswith(".pdf"):
        doc = pymupdf.open(pdf_path_or_dir)
        pages = ""
        for page in doc:
            text = page.get_text()
            pages += str(text)
        documents.append(Document(
            page_content=pages,
            metadata={"source": os.path.basename(pdf_path_or_dir), "type": "pdf"}
        ))
        doc.close()
    return documents

# Load training phrases from CSV files
def load_training_phrases(csv_path):
    documents = []
    if os.path.isdir(csv_path):
        for filename in os.listdir(csv_path):
            if filename.endswith(".csv"):
                # print(f"Loading training phrases")
                df = pd.read_csv(os.path.join(csv_path, filename), encoding="utf-8")
                for index, row in df.iterrows():
                    content = " ".join(str(value) for value in row.values if pd.notna(value))
                    # Create a Document object with metadata
                    documents.append(Document(
                        page_content=content,
                        metadata={"source": filename, "type": "training_phrase", "row": index}
                    ))
    return documents

# Embedder utility functions
def chunk_docs(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]  # Adjust separators as needed
        )
    return splitter.split_documents(documents)

def build_or_load_vectorstore(documents, index_path="index/faiss_store"):
    embeddings = OpenAIEmbeddings(
        api_key=os.environ.get('OPENAI_API_KEY'),
        model="text-embedding-3-small"
    )
    # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")  

    # Always delete the index_path directory before building, to ensure only new docs are embedded
    import shutil
    if os.path.exists(index_path):
        shutil.rmtree(index_path)

    chunks = chunk_docs(documents)
    if not chunks:
        return None
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(index_path)
    return vectorstore

def prompt(insurance_company: str, policy_number: str, policy_report_number: str, adjuster_name: str, adjuster_phone: str, claim_number: str, adjuster_email: str, user_full_name: str, email_address: str, user_phone_no: str):
    # Load advice from Training Phrases.csv
    advice_docs = load_training_phrases("data/")
    advice_text = "\n".join([f"- {doc.page_content}" for doc in advice_docs])

    # System prompt instructions for Benji
    system_message = (
        "You are Benji, a calm and strategic assistant helping users through insurance claims.\n"
        "Your personality:\n"
        "- Calm, never emotional\n"
        "- Strategic like a chess coach\n"
        "- Empathetic, warm, and confident\n"
        "Include editable templates when useful. Avoid robotic responses.\n"
        "When the user asks for a template, ALWAYS include ALL of their claim details in the template:\n"
        "- Insurance Company Name\n"
        "- Policy Number\n"
        "- Policy Report Number\n"
        "- Adjuster Name\n"
        "- Adjuster Phone Number\n"
        "- Claim Number\n"
        "- Adjuster Email\n"
        "Make sure every single piece of claim information is included in templates when requested.\n"
        "You strictly only answer questions related to insurance claims, claim processes, or insurance policy documents.\n"
        "If the user greets you (e.g., 'hi', 'hello', 'good morning', 'bye') respond politely as a normal chatbot would, but remind them you can only assist with insurance-related issues. For any non-insurance topic, say: 'Sorry, I can only help with insurance claim related questions.'\n"
        "If the user asks for a summary of the local policy PDF or any insurance document, provide a concise summary based on the local context.\n"
        "Keep responses concise and focused on the user's claim or policy. If user asked for his informations, provide it precisely. If any information is missing, say that information is missing.\n"
        "If the user asks for summary of the conversation, provide a summary of the chat history.\n"
        "Always remember the values of the given data of the user and when the user asks for his information, provide it precisely and accurately with the response.\n"
        "\nBest practices and advice for insurance claims:\n" + advice_text + "\n"
    )
    # User prompt template
    user_template = (
        "Context:\n{context}\n\n"
        "Conversation history:\n{chat_history}\n\n"
        "User question:\n{question}\n\n"
        "CLAIM DETAILS:\n"
        "- Insurance Company Name: {insurance_company}\n"
        "- Policy Number: {policy_number}\n"
        "- Policy Report Number: {policy_report_number}\n"
        "- Adjuster Name: {adjuster_name}\n"
        "- Adjuster Phone Number: {adjuster_phone}\n"
        "- Claim Number: {claim_number}\n"
        "- Adjuster Email: {adjuster_email}\n"
        "- User Full Name: {user_full_name}\n"
        "- Email Address: {email_address}\n"
        "- User Phone Number: {user_phone_no}\n\n"
        "Answer as Benji:"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_template)
    ])
    return prompt

def model_init():
    load_dotenv()
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=2048,
        openai_api_key=os.environ.get('OPENAI_API_KEY')
    )

    return llm

def chaining(insurance_company: str, policy_number: str, policy_report_number: str, adjuster_name: str, adjuster_phone: str, claim_number: str, adjuster_email: str, user_full_name: str, email_address: str, user_phone_no: str, global_knowledge="data/", local_knowledge="upload/", local_folder_name="local_knowledge"):
    load_dotenv()
    global_store = "index"
    local_store = os.path.join(global_store, local_folder_name)
    global_docs = load_pdfs(global_knowledge)
    global_vectorstore = build_or_load_vectorstore(global_docs, os.path.join(global_store, "faiss_store"))
    local_docs = load_pdfs(local_knowledge)
    local_vectorstore = build_or_load_vectorstore(local_docs, os.path.join(local_store, "faiss_store"))
    llm = model_init()
    prompt_template = prompt(insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no)
    def format_inputs(inputs):
        # If local_vectorstore is None, skip local context
        if local_vectorstore is not None:
            local_docs = local_vectorstore.as_retriever(search_kwargs={"k": 7}).invoke(inputs["question"])
            local_context = "\n\n".join([doc.page_content for doc in local_docs]) if local_docs else ""
        else:
            local_context = ""
        if global_vectorstore is not None:
            global_docs = global_vectorstore.as_retriever(search_kwargs={"k": 4}).invoke(inputs["question"])
            global_context = "\n\n".join([doc.page_content for doc in global_docs])
        else:
            global_context = ""
        
        if local_context.strip():
            combined_context = (
                f"[Local knowledge (User uploaded pdf context): {local_folder_name}]\n" + local_context + "\n\n[Global knowledge]\n" + global_context
            )
        else:
            combined_context = (
                f"[Local knowledge (User uploaded pdf context): {local_folder_name}]\n(No local context found. Only global context is available.)\n\n[Global knowledge]\n" + global_context
            )
        return {
            "context": combined_context,
            "chat_history": inputs.get("chat_history", ""),
            "question": inputs["question"],
            "insurance_company": inputs["insurance_company"],
            "policy_number": inputs["policy_number"],
            "policy_report_number": inputs["policy_report_number"],
            "adjuster_name": inputs["adjuster_name"],
            "adjuster_phone": inputs["adjuster_phone"],
            "claim_number": inputs["claim_number"],
            "adjuster_email": inputs["adjuster_email"],
            "user_full_name": inputs["user_full_name"],
            "email_address": inputs["email_address"],
            "user_phone_no": inputs["user_phone_no"]
        }
    chain = RunnableLambda(format_inputs) | prompt_template | llm | StrOutputParser()
    return chain

# Function to manage and return chat history as a list of dictionaries
# Accepts either a file path (str) or a list of dicts directly
def get_chat_history(history_source="chat_history.json"):
    if isinstance(history_source, list):
        return history_source
    elif isinstance(history_source, str):
        if os.path.exists(history_source):
            with open(history_source, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return []
    else:
        return []

def estimate_token_count(text):
    # Rough estimate: 1 token ≈ 4 characters (for English)
    return len(text) // 4

def trim_chat_history(history_list, max_tokens=2048):
    trimmed = []
    total_tokens = 0
    # Start from the most recent messages
    for msg in reversed(history_list):
        msg_text = f"User: {msg['human']}\nBenji: {msg['ai']}"
        msg_tokens = estimate_token_count(msg_text)
        if total_tokens + msg_tokens > max_tokens:
            break
        trimmed.insert(0, msg)  # Insert at the beginning to maintain order
        total_tokens += msg_tokens
    return trimmed

def get_history_text(history_list, max_tokens=2048):
    trimmed_history = trim_chat_history(history_list, max_tokens)
    return "\n".join([
        f"User: {msg['human']}\nBenji: {msg['ai']}" for msg in trimmed_history
    ])

def run_benji_chat(user, user_question, chat_history_list=None, upload_id=None):
    """
    Run Benji chat using user's claim information from database
    Args:
        user: Django User object or user_id string
        user_question: User's question
        chat_history_list: Optional chat history
        upload_id: Optional specific upload ID to use
    Returns:
        Tuple of (response, updated_chat_history_list)
    """
    if chat_history_list is None:
        chat_history_list = []

    # Get user claim information from database
    claim_info = get_user_claim_info(user, upload_id)
    
    # Extract individual values
    insurance_company = claim_info['insurance_company']
    policy_number = claim_info['policy_number']
    policy_report_number = claim_info['policy_report_number']
    adjuster_name = claim_info['adjuster_name']
    adjuster_phone = claim_info['adjuster_phone']
    claim_number = claim_info['claim_number']
    adjuster_email = claim_info['adjuster_email']
    user_full_name = claim_info['user_full_name']
    email_address = claim_info['email_address']
    user_phone_no = claim_info['user_phone_no']
    local_folder_name = claim_info['local_folder_name']
    upload_folder_path = claim_info['upload_folder_path']

    # Use upload folder path as local knowledge source
    local_pdf_path_or_folder = upload_folder_path if upload_folder_path and os.path.exists(upload_folder_path) else "data/"

    # Check if the uploaded PDF or folder exists
    local_pdf_exists = False
    if os.path.isdir(local_pdf_path_or_folder):
        pdfs = [f for f in os.listdir(local_pdf_path_or_folder) if f.lower().endswith('.pdf')]
        if pdfs:
            local_pdf_exists = True
    elif os.path.isfile(local_pdf_path_or_folder) and local_pdf_path_or_folder.lower().endswith('.pdf'):
        local_pdf_exists = True

    # Always clear the local vectorstore if a new file or directory is uploaded
    if local_pdf_exists:
        import shutil
        global_store = "index"
        local_store = os.path.join(global_store, local_folder_name)
        if os.path.exists(local_store):
            shutil.rmtree(local_store)

    chain = chaining(
        insurance_company, policy_number, policy_report_number, 
        adjuster_name, adjuster_phone, claim_number, adjuster_email, 
        user_full_name, email_address, user_phone_no, 
        local_knowledge=local_pdf_path_or_folder, 
        local_folder_name=local_folder_name
    )
    
    inputs = {
        "insurance_company": insurance_company,
        "policy_number": policy_number,
        "policy_report_number": policy_report_number,
        "adjuster_name": adjuster_name,
        "adjuster_phone": adjuster_phone,
        "claim_number": claim_number,
        "adjuster_email": adjuster_email,
        "user_full_name": user_full_name,
        "email_address": email_address,
        "user_phone_no": user_phone_no,
        "question": user_question,
        "chat_history": chat_history_list
    }
    
    response = chain.invoke({
        **inputs,
        "chat_history": get_history_text(chat_history_list, max_tokens=2048)
    })
    
    chat_history_list.append({"human": user_question, "ai": response})
    return response, chat_history_list


# Legacy function for backwards compatibility - now uses database
def run_benji_chat_legacy(insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no, user_question, chat_history_list=None, local_folder_name="custom_local_knowledge", local_pdf_path_or_folder="upload/"):
    """
    Legacy function for backwards compatibility
    This is kept to support existing code that calls the old signature
    """
    if chat_history_list is None:
        chat_history_list = []

    # Check if the uploaded PDF or folder exists
    local_pdf_exists = False
    if os.path.isdir(local_pdf_path_or_folder):
        pdfs = [f for f in os.listdir(local_pdf_path_or_folder) if f.lower().endswith('.pdf')]
        if pdfs:
            local_pdf_exists = True
    elif os.path.isfile(local_pdf_path_or_folder) and local_pdf_path_or_folder.lower().endswith('.pdf'):
        local_pdf_exists = True

    # Always clear the local vectorstore if a new file or directory is uploaded
    if local_pdf_exists:
        import shutil
        global_store = "index"
        local_store = os.path.join(global_store, local_folder_name)
        if os.path.exists(local_store):
            shutil.rmtree(local_store)

    chain = chaining(insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no, local_knowledge=local_pdf_path_or_folder, local_folder_name=local_folder_name)
    inputs = {
        "insurance_company": insurance_company,
        "policy_number": policy_number,
        "policy_report_number": policy_report_number,
        "adjuster_name": adjuster_name,
        "adjuster_phone": adjuster_phone,
        "claim_number": claim_number,
        "adjuster_email": adjuster_email,
        "user_full_name": user_full_name,
        "email_address": email_address,
        "user_phone_no": user_phone_no,
        "question": user_question,
        "chat_history": chat_history_list
    }
    response = chain.invoke({
        **inputs,
        "chat_history": get_history_text(chat_history_list, max_tokens=2048)
    })
    chat_history_list.append({"human": user_question, "ai": response})
    return response, chat_history_list

# # Example usage for local testing only
# if __name__ == "__main__":
#     def run_benji_chat(insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no, user_question, chat_history_list=None, local_folder_name="custom_local_knowledge", local_pdf_path_or_folder="upload/"):
#         if chat_history_list is None:
#             chat_history_list = []
#         def get_history_text(history_list):
#             return "\n".join([
#                 f"User: {msg['human']}\nBenji: {msg['ai']}" for msg in history_list
#             ])
#         chain = chaining(insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no, local_knowledge=local_pdf_path_or_folder, local_folder_name=local_folder_name)
#         inputs = {
#             "insurance_company": insurance_company,
#             "policy_number": policy_number,
#             "policy_report_number": policy_report_number,
#             "adjuster_name": adjuster_name,
#             "adjuster_phone": adjuster_phone,
#             "claim_number": claim_number,
#             "adjuster_email": adjuster_email,
#             "user_full_name": user_full_name,
#             "email_address": email_address,
#             "user_phone_no": user_phone_no,
#             "question": user_question,
#             "chat_history": chat_history_list
#         }
#         response = chain.invoke({
#             **inputs,
#             "chat_history": get_history_text(chat_history_list)
#         })
#         chat_history_list.append({"human": user_question, "ai": response})
#         return response, chat_history_list
    
#     # Example interaction
#     insurance_company = "Acme Insurance"
#     policy_number = "POL123456"
#     policy_report_number = "REP7890"
#     adjuster_name = "Jane Smith"
#     adjuster_phone = "555-123-4567"
#     claim_number = "CLM987654"
#     adjuster_email = "jane.smith@acme.com"
#     user_full_name = "John Doe"
#     email_address = "john.doe@email.com"
#     user_phone_no = "555-987-6543"
#     local_folder_name = "local_knowledge"
#     local_pdf_path = "upload/policy.pdf"  # Change this to your specific PDF path
#     chat_history_list = []
#     print("Welcome to Benji Insurance Chatbot!")
#     print("Type 'exit' to end the chat.")
#     while True:
#         user_question = input("You: ")
#         if user_question.strip().lower() == "exit":
#             print("Goodbye!")
#             break
#         response, chat_history_list = run_benji_chat(
#             insurance_company, policy_number, policy_report_number, adjuster_name, adjuster_phone, claim_number, adjuster_email, user_full_name, email_address, user_phone_no, user_question, chat_history_list, local_folder_name, local_pdf_path
#         )
#         print(f"Benji: {response}\n")


def create_claim_folder_structure(base_path, claim_info):
    """
    Create organized folder structure based on claim information
    Args:
        base_path: Base directory path
        claim_info: Dictionary with claim information
    Returns:
        Tuple of (organized_folder_path, folders_created_boolean)
    """
    try:
        # Create main claim folder
        claim_number = claim_info.get('add_claim_number', 'unknown_claim')
        insurance_company = claim_info.get('insurance_company_name', 'unknown_company')
        
        # Clean folder names (remove invalid characters)
        import re
        claim_number = re.sub(r'[<>:"/\\|?*]', '_', str(claim_number))
        insurance_company = re.sub(r'[<>:"/\\|?*]', '_', str(insurance_company))
        
        organized_folder = os.path.join(base_path, f"{insurance_company}_{claim_number}")
        
        # Create folder structure
        folders_to_create = [
            organized_folder,
            os.path.join(organized_folder, 'documents'),
            os.path.join(organized_folder, 'correspondence'),
            os.path.join(organized_folder, 'photos'),
            os.path.join(organized_folder, 'receipts')
        ]
        
        for folder in folders_to_create:
            os.makedirs(folder, exist_ok=True)
        
        # Save claim info to organized folder
        claim_info_file = os.path.join(organized_folder, 'claim_information.json')
        with open(claim_info_file, 'w') as f:
            json.dump(claim_info, f, indent=2)
        
        return organized_folder, True
        
    except Exception as e:
        print(f"Error creating organized folder structure: {e}")
        return base_path, False