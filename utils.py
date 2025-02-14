from redis_config import redis_client  
import json
import logging
from langchain_openai import ChatOpenAI
import os
from redis.exceptions import RedisError  

openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)

def refine_response(raw_text, query_type, user_query):
    """Uses OpenAI LLM to refine and extract the most relevant response with Redis caching."""

    logging.info(f"refine_response called with query_type={query_type}, user_query={user_query}")
    logging.debug(f"Raw Text Preview: {raw_text[:250]}")  

    if len(raw_text) < 100:
        logging.info("⚠️ Skipping LLM call: Raw text is too short.")
        return raw_text  

    cache_key = f"refined_response:{query_type}:{user_query.lower()}"
    cached_response = None

    if redis_client:
        try:
            cached_response = redis_client.get(cache_key)
            if cached_response:
                cached_response = cached_response.decode("utf-8") 
                logging.info(f" Cache hit! Returning cached refined response for: {user_query}")
                return cached_response
        except RedisError as e:
            logging.warning(f"⚠️ Redis error when retrieving cache: {str(e)}")

    prompt = f"""
    Extract only the **direct answer** to the following question from the provided text.
    Follow the specific extraction rules based on the query type:

    - **Company Overview**: Return a **concise summary** of the company's main industry, products, and key facts in **2-3 sentences max**.
    - **Business Model**: Return only the **key revenue sources** (e.g., "subscription services, advertising, cloud computing").
    - **Location**: Return only the **city and state** (or country if no state is available).
    - **Key People**: Return only the **names and roles** of key executives (e.g., "CEO: John Doe, CFO: Jane Smith").
    - **Products**: Return only the **main products or services** offered by the company (e.g., "Smartphones, cloud computing, and digital advertising").
    - **Investments**: Return only the **most recent investment amount, investors, and date**.
    - **Acquisitions**: Return only the **most recent acquisitions** with company names and date.
    - **Recent News**: Return **only the latest news headline and date**.
    - **Customers**: Return only the **types of customers** (e.g., businesses, individuals, industries, or key clients).
    - **Revenue**: Return only the **latest reported revenue amount**.
    
    **Query Type:** {query_type}
    **Question:** {user_query}
    **Text:** {raw_text}
    
    **Answer:** (Only return the exact required information)
    """

    refined_response = llm.invoke(prompt)

    if refined_response and hasattr(refined_response, "content"):  
        refined_text = refined_response.content.strip()

        # Store in Redis for Future Queries
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, refined_text) 
                logging.info(f" Cached refined response for {user_query} under key: {cache_key}")
            except RedisError as e:
                logging.warning(f"! Redis caching failed: {str(e)}")

        return refined_text  

    logging.warning("⚠️ LLM failed to generate refined response, returning raw text.")
    return raw_text  # Fallback if LLM fails

query_formatting = {
    "Acquisitions": lambda data: "\n".join([f"{company} was acquired on {date}" for company, date in data]),
    "Customers": lambda data: ", ".join(data.get("customer_types", ["Businesses", "Individuals", "Organizations"])),
    "Investments": lambda data: "\n".join([f"{firm} invested ${amount} million on {date}" for firm, amount, date in data]),
    "Revenue": lambda data: f"${data['amount']}B" if "B" in data['amount'] else f"${data['amount']}M" if "M" in data['amount'] else f"${data['amount']}"
}