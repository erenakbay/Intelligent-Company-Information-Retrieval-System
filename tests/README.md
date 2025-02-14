# Testing Documentation

## Overview

This test suite verifies the core functionalities involved in processing natural language queries to retrieve and refine company information. The tests cover multiple modules that interact with external services (like Redis for caching, Wikipedia for company verification, and simulated Language Learning Models for text refinement). For clarity, the suite is divided into four test scripts:

1. **test_utils.py** Verifies the text refinement logic.
2. **test_company_info.py** Checks the integrated behavior of data retrieval, response refinement, and query processing.

Each script uses a mix of fake objects, monkey patching, and mocking to simulate external dependencies, ensuring that tests run in isolation and do not depend on live systems.

---

# 📌 Test Suite Documentation  

## 1️⃣ File: `test_utils.py`

### **Purpose**
This module tests the `refine_response` function in the `utils` module. The function refines text by checking a **Redis cache** first, then invoking an **LLM** if necessary. The tests ensure correct behavior based on input conditions.

### **Functionality Tested**
- **Short Text Handling**  
  - If the input is **short** (less than 100 characters), the function should **return it unchanged**.

- **Text Refinement via LLM**  
  - If the input is **long enough**, the function should:
    - **Trigger an LLM call** if no cached version exists.  
    - Return the **LLM-refined response**.

- **Cache Usage (Redis)**  
  - If a **cached response** exists, return it **instead of calling the LLM**.  
  - If **Redis fails**, the function should **still return a valid response**.

### **Test Cases**
- **`test_refine_response_with_cache_hit`**  
  - **Scenario:** A refined response is **already cached** in Redis.  
  - **Expectation:** The function should return **the cached response** and **NOT call the LLM**.

- **`test_refine_response_with_cache_miss`**  
  - **Scenario:** Redis has **no cached response**, so the function must **use the LLM**.  
  - **Expectation:** The function should return the **LLM-refined text**.

- **`test_refine_response_with_redis_error`**  
  - **Scenario:** Redis encounters an **error** while retrieving cached data.  
  - **Expectation:** The function should **handle the error gracefully** and **return either the LLM response or the original input**.

- **`test_refine_response_with_short_text`**  
  - **Scenario:** The input text is **too short** for refinement.  
  - **Expectation:** The function should **return the input unchanged**.

---

## 2️⃣ File: `test_retrieval.py`

### **Purpose**
This module tests the `retrieve_information` function from the `data_retrieval` module. The function processes **company-related queries**, refines responses, and caches results in **Redis**.

### **Functionality Tested**
- **Successful Information Retrieval**  
  - Ensures valid queries **return structured data** including:  
    - **Company name**  
    - **Query type**  
    - **Refined response**  
    - **Confidence score**  
    - **Source information**

- **Redis Caching**  
  - If a **cached response** exists, the function should **return it instead of querying the LLM**.

- **Error Handling**  
  - Tests how the function **responds to failures**, such as:  
    - **Redis failures**  
    - **Invalid response formats from LLM**  
    - **Ambiguous queries**

### **Test Cases**

- **`test_retrieve_information_invalid_format`**  
  - **Scenario:** The **LLM returns an invalid response format**.  
  - **Expectation:** The function should detect this and return an **error message**.

- **`test_retrieve_information_cache`**  
  - **Scenario:** Redis **contains cached data** for the query.  
  - **Expectation:** The function should return **the cached response** and **NOT call the LLM**.

- **`test_retrieve_information_redis_failure`**  
  - **Scenario:** **Redis fails** while retrieving data.  
  - **Expectation:** The function should **raise a RedisError**.

- **`test_process_user_query_success`**  
  - **Scenario:** The function processes a **valid user query**.  
  - **Expectation:** It should correctly **extract the company name and query type**.

- **`test_process_user_query_ambiguous`**  
  - **Scenario:** The company name is **ambiguous** (multiple matches found).  
  - **Expectation:** The function should return **an ambiguity message** along with a **list of possible matches**.

- **`test_process_user_query_invalid`**  
  - **Scenario:** The query is **malformed or incorrect**.  
  - **Expectation:** The function should **return an error message**.

- **`test_process_user_query_api_failure`**  
  - **Scenario:** An **API failure** occurs while processing the query.  
  - **Expectation:** The function should **return an error message** instead of crashing.

---

## Conclusion

The testing suite is designed to ensure that:

- **Efficiency:** The system bypasses unnecessary external calls when a response is already cached or when input does not require refinement.
- **Accuracy:** Refined responses, company name extraction, and query parsing are validated through carefully simulated scenarios.
- **Resilience:** The system gracefully handles ambiguous queries and errors, providing clear instructions or fallback responses when necessary.

By using realistic mock objects and controlled test cases, the suite verifies all critical paths�from text refinement through to data retrieval and user query processing�ensuring robust, user-friendly behavior in production.
