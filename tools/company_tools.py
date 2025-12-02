"""
Company Info Tools (RAG-based)

Tools for searching company documents using RAG.
"""

from langchain_core.tools import tool
from tools.utils.rag_utils import search_company_vector_db


@tool
def search_company_documents(query: str) -> str:
    """
    Search company documents for information about policies, procedures, contact details, 
    shipping, returns, warranties, business hours, and more.
    
    Use this tool when the user asks about:
    - Company information (contact, phone, email, address, location)
    - Business hours and operating times
    - Shipping and delivery policies
    - Return and refund policies
    - Warranties and guarantees
    - Terms and conditions
    - Any other company policies or procedures
    
    Args:
        query: The question or topic to search for in company documents
    
    Returns:
        Relevant information from company documents
    """
    # Search the vector database
    results = search_company_vector_db(query, k=5)
    
    if not results:
        return f"""I couldn't find specific information about "{query}" in the company documents.

This could mean:
• The company documents haven't been indexed yet
• The information isn't available in the current documents

Please contact customer service for assistance:
• Phone: 1-800-WAREHOUSE
• Email: support@warehousesupply.com
"""
    
    # Format the results
    response = f"Company Information: {query}\n\n"
    
    # Combine relevant chunks (avoid duplicates)
    seen_content = set()
    relevant_content = []
    
    for result in results:
        content = result["content"].strip()
        # Simple deduplication by checking first 100 chars
        content_key = content[:100] if len(content) > 100 else content
        if content_key not in seen_content:
            seen_content.add(content_key)
            relevant_content.append(content)
    
    if relevant_content:
        response += "\n\n---\n\n".join(relevant_content)
    else:
        response += "No relevant information found."
    
    return response
