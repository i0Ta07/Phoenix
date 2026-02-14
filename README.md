# Phoenix - Agentic Chatbot

A production-ready conversational AI agent built with **LangGraph** and **Streamlit**, featuring persistent memory with PostgreSQL, real-time streaming, multi-tool integration, and document/video Q&A capabilities with full observability.

## Core Features

### 🧠 Persistent Memory

* **PostgreSQL-based checkpoint persistence** for production-grade reliability
* Thread-based conversation storage across sessions
* Reload previous conversations seamlessly
* Short-term memory implementation for context-aware responses

### ⚡ Real-Time Streaming

* **Token-by-token streaming** for improved user experience
* Live tool execution feedback (e.g., "Calling get_weather... Processing... Done")
* Asynchronous response generation with visual indicators

### 🛠️ Multi-Tool Integration

Four production-ready tools with streaming output:

1. **Calculator** - Mathematical computations
2. **DuckDuckGo Search** - Web search integration
3. **Currency Converter** - Real-time exchange rates
4. **Weather API** - Current weather data

### 📄 PDF Question Answering

* Upload **one PDF per chat**
* Ask questions grounded strictly in that document
* RAG-based retrieval for accurate answers
* To query another PDF, start a **new chat**

### 🎥 YouTube Video Q&A

* Provide **one YouTube video per chat**
* Ask questions based on the video transcript
* Semantic search across video content
* To analyze a different video, start a **new chat**

### 🔍 Full Observability

* **LangSmith integration** for debugging and monitoring
* Trace all LLM calls, tool executions, and agent decisions
* Performance analytics and error tracking

### 💻 Interactive Frontend

* Built with **Streamlit** for rapid prototyping
* Clean, responsive UI with real-time updates
* Easy deployment and customization

## Setup

### Prerequisites

* Python 3.10+
* [uv](https://github.com/astral-sh/uv) package manager
* PostgreSQL 12+ installed and running
* API keys for:
  * OpenAI
  * LangSmith (for observability)
  * ExchangeRate API

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/i0Ta07/Phoenix
cd Phoenix
```

2. **Install dependencies**

```bash
uv sync
```

3. **Set up PostgreSQL database**

```bash
-- Create the user 
CREATE USER phoenix_user WITH PASSWORD 'your_password';

-- Create the database with this user as owner
CREATE DATABASE phoenix_db OWNER phoenix_user;

-- Connect to the new database
\c phoenix_db

-- Grant schema privileges (phoenix_user already owns the database, but this ensures they can create objects)
GRANT ALL PRIVILEGES ON SCHEMA public TO phoenix_user;

-- For future tables/sequences created by ANY user, grant access to phoenix_user
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO phoenix_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO phoenix_user;
```

4. **Configure environment variables**

Create a `.env` file in the root directory:

```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# LangSmith Observability
LANGSMITH_API_KEY=your_langsmith_key
LANGCHAIN_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=phoenix

# ExchangeRate API
EXCHANGE_API_KEY=your_exchange_rate_api_key

# PostgreSQL Database
DB_URL="postgresql://phoenix_user:your_password@localhost:5432/phoenix_db"
```

5. **Launch the application**

```bash
cd main
uv run streamlit run frontend.py
```

## UI

![UI](ui.png "UI")

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments

Built with [LangChain](https://langchain.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), and [Streamlit](https://streamlit.io/)
