import os
import time
import datetime
import logging
from dotenv import load_dotenv
from langsmith import traceable, Client
from langchain_community.tools import TavilySearchResults
from langgraph.graph import StateGraph
from langchain_openai import OpenAI
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from pydantic import BaseModel
from user_query import process_user_query 
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from utils import refine_response  
import wikipedia
from redis_config import redis_client  
from redis.exceptions import RedisError
import json

# Load environment variables from .env file
load_dotenv()

# Retrieve API Keys 
WIKIPEDIA_API_KEY = os.getenv("WIKIPEDIA_ACCESS_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

clarification_store = {}

# LangSmith Initialization
langsmith_client = Client(api_key=LANGSMITH_API_KEY) if LANGSMITH_TRACING else None

# Configure Logging
logging.basicConfig(
    filename="system_logs.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# GPT Initialization
llm = OpenAI(model="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Wikipedia & Tavily Tools
wikipedia_api = WikipediaAPIWrapper(api_key=WIKIPEDIA_API_KEY)
wikipedia_tool = WikipediaQueryRun(api_wrapper=wikipedia_api)
tavily_tool = TavilySearchResults(k=3, tavily_api_key=TAVILY_API_KEY)

class RetrievalState(BaseModel):
    query: str
    query_type: str
    wiki_result: str = None
    wiki_source: str = None  
    tavily_result: str = None
    tavily_source: str = None  
    final_result: str = None

def build_graph():
    """Defines the LangGraph workflow for retrieval & processing."""
    graph = StateGraph(RetrievalState)  
    
    def start_node(state):
        logging.info(f"Starting graph with query: {state.query}")
        return state  
    
    graph.add_node("START", start_node)

    def query_wikipedia(state):
        """Fetches data from Wikipedia with URLs."""
        retries = 2  
        for attempt in range(retries):
            try:
                search_results = wikipedia.search(state.query)

                if not search_results:
                    return {
                        "wiki_result": "No relevant Wikipedia content found.", "wiki_source": "No Wikipedia source available."}

                # Take the first search result as the most relevant page
                page_title = search_results[0]
                wiki_page = wikipedia.page(page_title, auto_suggest=False)
                wiki_url = wiki_page.url
                extracted_text = wiki_page.content[:500] 

                return {"wiki_result": extracted_text, "wiki_source": wiki_url}

            except Exception as e:
                logging.error(f"Wikipedia retrieval failed (Attempt {attempt+1}): {e}")
                time.sleep(1)  

        return {
            "wiki_result": "! Wikipedia query failed.",
            "wiki_source": "No Wikipedia source available."
        }

    def extract_relevant_text(text, query):
        """Extracts the most relevant paragraph from a Wikipedia summary."""
        paragraphs = text.split("\n")  
        relevant_paragraphs = [p for p in paragraphs if query.lower() in p.lower()]
        return relevant_paragraphs[0] if relevant_paragraphs else text[:500]  

    def query_tavily(state):
        '''Fetches data from Tavily with URLs.'''
        retries = 2  
        for attempt in range(retries):
            try:
                tavily_tool = TavilySearchResults(k=3, tavily_api_key=TAVILY_API_KEY)
                tavily_response = tavily_tool.run(state.query)

                if isinstance(tavily_response, list) and len(tavily_response) > 0:
                    extracted_text = tavily_response[0].get("content", "No relevant text found.")
                    filtered_text = extract_relevant_text(extracted_text, state.query)
                    source_url = tavily_response[0].get("url", "No Tavily source available.")
                else:
                    filtered_text = "No relevant data found."
                    source_url = "No Tavily source available."

                if filtered_text.strip():
                    return {"tavily_result": filtered_text, "tavily_source": source_url}
                
            except Exception as e:
                logging.error(f"Tavily retrieval failed (Attempt {attempt+1}): {e}")
                time.sleep(1)  

        return {"tavily_result": "! Tavily query failed.", "tavily_source": "No Tavily source available."}

    # Processing Node 
    def process_results(state, retry_count=0, max_retries=2):
        """Processes Wikipedia & Tavily results, refines the query if needed, and assigns confidence scores."""
        wiki_result = getattr(state, "wiki_result", None)
        wiki_source = getattr(state, "wiki_source", None)
        tavily_result = getattr(state, "tavily_result", None)
        tavily_source = getattr(state, "tavily_source", None)

        logging.info(f"Wikipedia Result -> {wiki_result}")  
        logging.info(f"Tavily Result -> {tavily_result}")  

        if not wiki_result and not tavily_result:
            if retry_count < max_retries:
                logging.info(f"⚠️ No results found. Refining query and retrying... (Attempt {retry_count + 1})")
                refined_query = f"{state.query} detailed explanation"
                state.query = refined_query
                return process_results(build_graph().invoke(state), retry_count + 1)  # Retry with refined query
            
            logging.warning("Max retries reached. No results found.")
            return {"final_result": "! No relevant data found after multiple attempts.", "confidence_score": 0.0, "source": "N/A"}

        if wiki_result and not tavily_result:
            best_result = wiki_result
            source = f" Wikipedia: {wiki_source}" if wiki_source else "No Wikipedia source available."
        elif tavily_result and not wiki_result:
            best_result = tavily_result
            source = f" Tavily: {tavily_source}" if tavily_source else "No Tavily source available."
        else:
            best_result = f"{wiki_result}\n\n{tavily_result}"
            source = f" Wikipedia: {wiki_source if wiki_source else 'No Wikipedia source'}\n Tavily: {tavily_source if tavily_source else 'No Tavily source'}"

        if wiki_result and tavily_result:
            confidence_score = 0.9 if wiki_result[:100] in tavily_result else 0.8  # Heuristic
        elif wiki_result or tavily_result:
            confidence_score = 0.7  # One source available
        else:
            confidence_score = 0.5  # Weak data

        refined_text = refine_response(best_result, state.query_type, state.query)

        refined = {
            "response": refined_text,
            "confidence_score": confidence_score,
            "source": source.strip() if source else "No sources available."
        }

        logging.info(f" Refined Response -> {refined}")  
        return {"final_result": refined}

    graph.add_node("wikipedia", query_wikipedia)
    graph.add_node("tavily", query_tavily)
    graph.add_node("process_results", process_results)

    graph.add_edge("START", "wikipedia")  
    graph.add_edge("START", "tavily")  
    graph.add_edge("wikipedia", "process_results")
    graph.add_edge("tavily", "process_results")

    graph.set_entry_point("START")

    return graph

# Initialize Graph Workflow
graph = build_graph()
graph = graph.compile()

@traceable
def retrieve_information(user_query):
    """Retrieves structured company data using LangChain + LangGraph error handling and LangSmith tracing."""
    logging.info(f"Received user query: {user_query}")
    query_data = process_user_query(user_query) 

    if "ambiguous_options" in query_data:
        logging.warning(f"⚠️ Query is ambiguous: {query_data['ambiguous_options']}")

        if redis_client:
            redis_client.setex(f"ambiguity:{user_query}", 600, json.dumps(query_data["ambiguous_options"]))

        clarification_store[user_query] = query_data["ambiguous_options"]

        return {
            "message": "Your query is ambiguous.",
            "options": query_data["ambiguous_options"],
            "next_step": "Please select one of the options using the /clarify/ endpoint."
        }

    cache_key = f"company_info:{query_data['company_name'].lower()}:{query_data['query_type'].lower()}"
    cached_response = redis_client.get(cache_key) if redis_client else None

    if cached_response:
        logging.info(f"Cache hit for query: {user_query}")
        return json.loads(cached_response)  

    logging.info(f"! Cache miss for query: {user_query}, processing...")

    # Process Query Using Graph
    structured_query = query_data["structured_query"]
    logging.info(f"Processed Query -> {structured_query} [{query_data['query_type']}]")

    initial_state = RetrievalState(query=structured_query, query_type=query_data["query_type"])

    try:
        start_time = time.time()
        logging.info(" Starting LangGraph execution with LangSmith tracing...")

        # LangGraph to Fetch Data
        final_state = graph.invoke(initial_state)
        elapsed_time = round(time.time() - start_time, 2)
        logging.info(f" Graph Execution Completed in {elapsed_time}s")

        if isinstance(final_state, dict) and "final_result" in final_state:
            response_content = final_state["final_result"]
            logging.info(f" Final Retrieved Response: {response_content}")

            response = {
                "company_name": query_data["company_name"],
                "query_type": query_data["query_type"],
                "response": response_content.get("response", "Error: No final result found."),
                "confidence_score": response_content.get("confidence_score", 0.0),
                "source": response_content.get("source", "No sources available."),
                "citation_url": response_content.get("source", "No citation URL available."),
            }

            if redis_client:
                try:
                    redis_client.setex(cache_key, 3600, json.dumps(response)) 
                    logging.info(f" Stored query result in cache: {cache_key}")
                except RedisError as e:
                    logging.error(f"Redis caching failed: {e}")

            return response  

        logging.error(" Invalid final state format received.")
        return {
            "company_name": query_data["company_name"],
            "query_type": query_data["query_type"],
            "response": "Error: Invalid response format.",
            "confidence_score": 0.0,
            "source": "No sources available.",
            "citation_url": "N/A",
        }

    except Exception as e:
        logging.exception(f" Unexpected Error in retrieve_information: {e}")
        return {
            "company_name": "Unknown",
            "query_type": "Unknown",
            "response": "An internal error occurred. Please try again later.",
            "confidence_score": 0.0,
            "source": "No sources available.",
            "citation_url": "N/A",
        }