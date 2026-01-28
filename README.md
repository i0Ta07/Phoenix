# LangGraph Chatbot with Persistence

A production-ready conversational AI agent built with **LangGraph** and  **Streamlit** , featuring persistent memory, real-time streaming, and multi-tool integration with full observability.

## Core Features

### Persistent Memory

* **Thread-based checkpoint persistence** using SQLite (`threads.db`)
* Reload previous conversations seamlessly across sessions
* Short-term memory implementation for context-aware responses

### Real-Time Streaming

* **Token-by-token streaming** for improved user experience
* Live tool execution feedback (e.g., "Calling get_weather... Processing... Done")
* Asynchronous response generation with visual indicators

### Multi-Tool Integration

Four production-ready tools with streaming output:

1. **Calculator** - Mathematical computations
2. **DuckDuckGo Search** - Web search integration
3. **Currency Converter** - Real-time exchange rates
4. **Weather API** - Current weather data

### Full Observability

* **LangSmith integration** for debugging and monitoring
* Trace all LLM calls, tool executions, and agent decisions
* Performance analytics and error tracking

### Interactive Frontend

* Built with **Streamlit** for rapid prototyping
* Clean, responsive UI with real-time updates
* Easy deployment and customization

## Setup

### Prerequisites

* Python 3.10+
* [uv](https://github.com/astral-sh/uv) package manager
* API keys for:
  * OpenAI
  * LangSmith (for observability)
  * Exchange RateAPI (exchangerate-api)

### Installation

1. **Clone the repository**

bash

```bash
git clone https://github.com/i0Ta07/Phoenix
cd Phoenix
```

2. **Install dependencies**

bash

```bash
   uv sync
```

3. **Configure environment variables**
   Create a `.env` file in the root directory:

env

```env
   OPENAI_API_KEY=your_openai_key
   LANGSMITH_API_KEY=your_langsmith_key
   LANGCHAIN_TRACING_V2=true
   LANGSMITH_ENDPOINT=langsmith_endpoint
   LANGCHAIN_PROJECT=default
   EXCHANGE_API_KEY=your_exhange_rate_api_key
```

4. **Navigate to main directory and launch**

bash

```bash
cd main
uv run streamlit run frontend.py
```
