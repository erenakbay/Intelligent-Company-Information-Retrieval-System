from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
import os
import json
import wikipedia
import logging
from redis_config import redis_client

# Store for Ambiguity Handling 
clarification_store = {}

llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))

# prompt template
query_template = PromptTemplate(
    input_variables=["query"],
    template="""
    Extract the company name and classify the query into one of these categories:
    - Company Overview (General information about the company)
    - Business Model (How does the company make money?)
    - Location (Where is the company headquartered?)
    - Key People (Who are the key executives or founders?)
    - Products (What products or services does the company offer?)
    - Investments (What are the company’s latest investments?)
    - Acquisitions (What companies has the company acquired?)
    - Recent News (What is the latest news about the company?)
    - Customers (Who are the company’s main customers?)
    - Revenue (How much revenue does the company generate?)

    If the company is highly recognizable (e.g., Tesla, Google, Microsoft), do not return "ambiguous."

    If the company does not exist, return:
    "Error: Could not find any company with this name."

    Query: {query}
    
    Respond strictly in this format:
    Company Name: [company]
    Category: [category]
    """
)

query_chain = RunnableSequence(query_template | llm)

def verify_company_name(company_name):
    """Verifies if a company name is ambiguous or non-existent using Wikipedia and LLM."""
    try:
        search_results = wikipedia.search(company_name)

        if not search_results:
            return {"error": f"Company not found: '{company_name}' does not exist."}

        normalized_results = [res.lower() for res in search_results]
        normalized_company_name = company_name.lower()

        if normalized_company_name in normalized_results:
            return {"verified": company_name}
        if company_name.lower() in search_results[0].lower():
            return {"verified": search_results[0]}
        if len(search_results) > 1:
            return {
                "ambiguous": True,
                "message": f"Multiple companies found for '{company_name}'. Please clarify.",
                "options": search_results[:5], 
            }

        return check_company_with_llm(company_name)

    except Exception as e:
        return {"error": f"Failed to verify company: {str(e)}"}

def check_company_with_llm(company_name):
    """Uses LLM to determine if a company is real or ambiguous."""
    prompt = f"""
    You are an expert business analyst. Determine if '{company_name}' refers to a well-known company or if it is ambiguous.

    Respond in one of the following formats:
    - "Verified: [company_name]" if the company is real and unambiguous.
    - "Ambiguous: [option1], [option2], [option3]" if multiple companies could match.
    - "Unknown: [company_name]" if no company exists with that name.

    Return only the classification and the company name(s).
    """

    response = llm.invoke(prompt)
    if response and hasattr(response, "content"):
        content = response.content.strip()

        if content.startswith("Verified:"):
            return {"verified": content.replace("Verified:", "").strip()}
        elif content.startswith("Ambiguous:"):
            options = content.replace("Ambiguous:", "").strip().split(", ")
            return {
                "ambiguous": True,
                "message": f"Multiple companies match '{company_name}'. Please clarify.",
                "options": options
            }

        return {"error": f"Company not found: '{company_name}' does not exist."}
    return {"error": "Failed to verify company via LLM."}

def process_user_query(user_query):
    """Extracts company name and query type from user input."""
    response = query_chain.invoke({"query": user_query})

    if not hasattr(response, "content"):
        return {"error": "Invalid LLM response format.", "raw_response": str(response)}

    content = response.content.strip().split("\n")
    content = [line.strip() for line in content if line.strip()]

    if len(content) < 2 or not content[0].startswith("Company Name:") or not content[1].startswith("Category:"):
        return {"error": "Failed to extract company name or category.", "raw_response": content}

    company_name = content[0].replace("Company Name:", "").strip()
    query_type = content[1].replace("Category:", "").strip()

    verification_result = verify_company_name(company_name)

    if "ambiguous" in verification_result:
        logging.warning(f"! Query is ambiguous: {verification_result['options']}")

        #  Store in Redis
        if redis_client:
            redis_client.setex(f"ambiguity:{user_query}", 600, json.dumps(verification_result["options"])) 

        clarification_store[user_query] = verification_result["options"]

        return {
            "message": "Your query is ambiguous.",
            "options": verification_result["options"],
            "next_step": "Please select one of the options using the /clarify/ endpoint."
        }

    if "error" in verification_result:
        return verification_result  # Return error if company is not found

    query_map = {
        "Company Overview": f"General information about {company_name}",
        "Business Model": f"How does {company_name} make money?",
        "Location": f"{company_name} headquarters location",
        "Key People": f"Who are the key executives of {company_name}?",
        "Products": f"What products or services does {company_name} offer?",
        "Investments": f"Recent investments by {company_name}",
        "Acquisitions": f"Recent acquisitions by {company_name}",
        "Recent News": f"Latest news about {company_name}",
        "Customers": f"Who are the customers of {company_name}?",
        "Revenue": f"What is the revenue of {company_name}?"
    }

    structured_query = query_map.get(query_type, f"Information about {company_name}")

    return {
        "query": user_query,
        "company_name": company_name,
        "query_type": query_type,
        "structured_query": structured_query
    }
