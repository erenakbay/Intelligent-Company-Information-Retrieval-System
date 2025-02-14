# Company Information Retrieval & Analysis

A robust multi-source company information retrieval system that processes natural language queries to extract and present key data about companies. This project leverages advanced LLMs, LangChain workflows, and LangGraph for orchestrating data pipelines, integrating external APIs (e.g., Wikipedia and Tavily). It includes Redis caching, LangSmith tracing for detailed workflow insights, and is built with FastAPI to serve a RESTful API. The entire system is fully containerized with Docker Compose.


---

## Features

### 🔍 Query Parsing & Verification
- Extracts the company name and query category (e.g., Company Overview, Business Model, Location, etc.) using a prompt-driven LLM chain.
- Verifies and disambiguates company names using Wikipedia searches and LLM-based fallback.
- Handles ambiguous queries by suggesting multiple company options.

### 📊 Data Retrieval & Processing
- Implements a **LangGraph** workflow with dedicated nodes for retrieving data from Wikipedia and Tavily.
- Merges and refines data using heuristic confidence scoring.
- Uses **OpenAI’s ChatOpenAI model** for final output refinement.

### 🖥️ Backend API (FastAPI)
- Provides a **RESTful API** for handling queries and resolving ambiguities.
- Supports endpoints like `/clarify/` for handling ambiguous company searches.

### 🔎 Tracing & Monitoring (LangSmith)
- Integrates **LangSmith** for tracing and monitoring LangGraph workflows.
- Offers real-time insights into data retrieval and processing steps.

### ⚡ Caching with Redis
- Caches responses and ambiguity options to reduce redundant external API calls.

### 🐳 Containerized Deployment
- Fully **Dockerized** using Docker Compose, making deployment seamless with Redis as a service.

---

## Project Architecture

### 1️⃣ User Query Processing
- Uses **RunnableSequence** to extract structured information from natural language queries.
- Verifies company names using Wikipedia and LLM analysis.
- Handles ambiguous or non-existent company searches.

### 2️⃣ Data Retrieval Workflow (LangGraph)
- **Wikipedia Retrieval:** Fetches relevant content from Wikipedia.
- **Tavily Retrieval:** Retrieves additional context from Tavily.
- **Result Processing:** Merges, refines, and scores results from both sources.
- **Tracing:** Uses **LangSmith** to capture execution metrics and debug information.

### 3️⃣ Response Refinement
- Uses OpenAI’s **ChatOpenAI** model to refine responses.
- Stores the refined answer, along with metadata like confidence score and source details, in Redis.

### 4️⃣ Backend API
- **FastAPI-based** backend serves endpoints for handling queries, returning refined responses, and managing ambiguity resolution.

---

## Technologies Used

- **FastAPI** – RESTful API framework
- **LangChain & LangGraph** – Orchestration of LLM workflows
- **LangSmith** – Tracing & monitoring execution
- **Redis** – Caching responses and managing ambiguity options
- **Docker & Docker Compose** – Containerization
- **Python** – Primary programming language

---

## Requirements

- **Python** 3.8 or later
- **Docker & Docker Compose**
- **Redis** (Managed via Docker)

### 📦 Python Dependencies
Refer to `requirements.txt` for a complete list, including:

```txt
fastapi
uvicorn
langchain
langgraph
langsmith
wikipedia
redis
pydantic
python-dotenv
```

---

## Installation

### 🔧 Set Up a Virtual Environment & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the root directory with:

```env
# OpenAI & LLM Keys
OPENAI_API_KEY=your_openai_api_key

# API Keys for External Services
WIKIPEDIA_ACCESS_TOKEN=your_wikipedia_api_key
TAVILY_API_KEY=your_tavily_api_key

# LangSmith Configuration
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true  # Set to 'false' to disable tracing
LANGSMITH_PROJECT=your_langsmith_project_name
```

---

## Running the Project

### 🐳 Using Docker Compose

```bash
docker-compose up --build
```

This builds your application image, starts the Redis container, and sets up the necessary network configurations.

### 🏗️ Local Development (Without Docker)
Ensure Redis is running and start the FastAPI application with:

```bash
uvicorn main:app --reload
```

(Replace `main:app` with the actual module if different.)

---

## Logging, Tracing & Monitoring

### 📜 Logging
- Application logs are saved to `system_logs.log` for ongoing monitoring and debugging.

### 📊 LangSmith Tracing
- Provides detailed execution insights into your LangGraph workflow.
- Helps track performance and debug issues in real-time.

---

## API Endpoints & Usage

### 🤔 Ambiguity Handling
- If a query is ambiguous, the system suggests multiple companies.
- Users can resolve ambiguity via the `/clarify/` endpoint.

### 📌 Final Response Structure
Each query returns a JSON response containing:

```json
{
  "company_name": "Example Corp",
  "query_type": "Business Model",
  "response": "Example Corp operates a subscription-based model...",
  "confidence_score": 0.92,
  "source": ["Wikipedia", "Tavily"]
}
```

---

## Contributing

Contributions are welcome! 🎉

1. **Fork** the repository.
2. **Implement** your changes.
3. **Submit** a pull request.

Ensure tests and documentation are updated for new functionality. 🚀

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

