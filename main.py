from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from data_retrieval import retrieve_information, redis_client
import json

app = FastAPI(
    title="Intelligent Company Information Retrieval System",
    description="API for retrieving structured and real-time company data.",
    version="1.0",
    docs_url="/docs",  
    redoc_url="/redoc" 
)

clarification_store = {}

class QueryResponse(BaseModel):
    company_name: str
    query_type: str
    response: str
    confidence_score: float
    source: str
    citation_url: str

class AmbiguousResponse(BaseModel):
    message: str
    options: list[str]
    next_step: str

@app.get("/query/")
def process_query(user_query: str = Query(..., description="The user's query (e.g., 'Where is OpenAI headquartered?')")):
    """API endpoint to handle user queries with Redis caching & ambiguity handling."""
    cache_key = f"query_result:{user_query.lower()}"
    
    cached_response = redis_client.get(cache_key) if redis_client else None
    if cached_response:
        print(f" Cache hit for query: {user_query}")
        return json.loads(cached_response)  # Return cached result immediately
    
    print(f"⚠️ Cache miss for query: {user_query}, processing...")

    response = retrieve_information(user_query)

    if "ambiguous" in response:
        ambiguity_key = f"ambiguity:{user_query.lower()}"

        if redis_client:
            redis_client.setex(ambiguity_key, 3600, json.dumps(response["options"]))  
        else:
            clarification_store[user_query] = response["options"]  
        
        return AmbiguousResponse(
            message=response["message"],
            options=response["options"],
            next_step="Use the /clarify/ endpoint to select the correct company."
        )

    # Store the Final Response in Redis
    if redis_client:
        redis_client.setex(cache_key, 3600, json.dumps(response))  

    return QueryResponse(**response)

@app.get("/clarify/")
def clarify_query(selection: str = Query(..., description="Selected company from the options")):
    """Handles follow-up queries for ambiguous results using Redis or an in-memory store."""

    if redis_client:
        keys = redis_client.keys("ambiguity:*")  
        for key in keys:
            options = json.loads(redis_client.get(key))
            if selection in options:
                original_query = key.replace("ambiguity:", "")
                refined_query = f"{original_query} (referring to {selection})"

                redis_client.delete(key)  
                
                return retrieve_information(refined_query)

    # Fallback
    for query, options in clarification_store.items():
        if selection in options:
            refined_query = f"{query} (referring to {selection})"
            del clarification_store[query]  # Remove ambiguity after resolution
            return retrieve_information(refined_query)

    raise HTTPException(status_code=400, detail="Invalid selection. Please choose from the provided options.")

@app.post("/clear-cache/")
def clear_cache():
    """Clears all cached data from Redis."""
    if redis_client:
        redis_client.flushdb()  # Clears all keys
        return {"message": " Redis cache cleared successfully"}
    return {"error": " Redis is not connected"}
