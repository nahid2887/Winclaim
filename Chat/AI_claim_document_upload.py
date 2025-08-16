from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pymupdf

def model_init(claim_no: int, list_item: list[str], name: str, phone: str, email: str, policy: str, receipt: str):
    load_dotenv()
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=2048,
        openai_api_key=os.environ.get('OPENAI_API_KEY')
    )

    template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert insurance claim processor and document analyzer. Your role is to generate comprehensive claim analysis reports by consolidating information from multiple sources. You must preserve ALL numerical data, dates, amounts, policy numbers, and specific details without any approximation or loss of precision."""),
        ("user", """Generate a comprehensive insurance claim analysis report using the provided information:

        CLAIM DETAILS:
        - Claim Number: {claim_no}
        - Claimant Name: {name}
        - Contact Phone: {phone}
        - Contact Email: {email}
        - Claimed Items: {list_item}

        POLICY DOCUMENT:
        {policy}

        RECEIPT/DOCUMENTATION:
        {receipt}

        ANALYSIS REQUIREMENTS:
        1. CLAIM VALIDATION: Cross-reference the claimed items against policy coverage and provided receipts
        2. NUMERICAL ACCURACY: Preserve ALL exact amounts, dates, policy numbers, and quantities
        3. COVERAGE ASSESSMENT: Determine coverage eligibility for each claimed item
        4. DISCREPANCY IDENTIFICATION: Highlight any inconsistencies between policy, receipts, and claimed items
        5. FINANCIAL SUMMARY: Calculate total claim amount, covered amounts, deductibles, and out-of-pocket costs
        6. RECOMMENDATIONS: Provide approval/denial recommendations with detailed justifications

        OUTPUT FORMAT:
        Structure your response with clear sections including:
        - Executive Summary
        - Claim Details Verification
        - Item-by-Item Analysis
        - Financial Breakdown (with exact figures)
        - Policy Compliance Assessment
        - Final Recommendations
        - Required Next Steps

        CRITICAL: Maintain complete accuracy of all numbers, dates, names, and financial data. Do not round, approximate, or omit any numerical information.""")])
    
    chain = template | llm | StrOutputParser()
    
    return chain

# Load PDF
def load_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)
    pages = ""
    
    for page in doc:
        text = page.get_text().encode("utf-8")
        # print(text)
        pages += str(text)
    return pages

def main(claim_no: int, list_item: list[str], name: str, phone: str, email: str, pdf1: str = "pdf1.pdf", pdf2: str = "pdf2.pdf"):
    # Load and summarize policy document
    policy = load_pdf(pdf1)
    receipt = load_pdf(pdf2)

    # Generate comprehensive claim analysis
    claim_analysis_chain = model_init(claim_no, list_item, name, phone, email, policy, receipt)
    
    # Generate final claim analysis report
    final_response = claim_analysis_chain.invoke({
        "claim_no": claim_no,
        "name": name,
        "phone": phone,
        "email": email,
        "list_item": list_item,
        "policy": policy,
        "receipt": receipt
    })
    
    return final_response