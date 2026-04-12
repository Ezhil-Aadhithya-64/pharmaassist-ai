# 🤖 PharmaAssist AI — Multi-Agent Customer Service System

> Production-grade agentic AI system for pharmacy e-commerce, built with LangGraph orchestration, tool calling, and RAG

An intelligent customer service platform that autonomously handles order management, policy queries, and complex multi-step workflows through coordinated AI agents. Demonstrates real-world application of agentic AI patterns including dynamic routing, stateful memory, and tool-augmented generation.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Why This Project Matters

Traditional chatbots follow rigid decision trees. This system uses **agentic AI** — autonomous agents that:
- Dynamically route requests based on intent classification
- Execute database operations through tool calling
- Maintain conversation context across sessions
- Coordinate multiple specialized agents for complex workflows
- Make decisions without hardcoded rules

This architecture mirrors production systems at companies building AI-native customer service platforms.

---

## 🚀 Key Capabilities

- **🧠 Multi-Agent Orchestration** — LangGraph state machine with 9 specialized nodes
- **🎯 Intent Classification** — Zero-shot intent detection with entity extraction
- **🔧 Tool Calling** — LLM-driven database operations (cancel, refund, modify orders)
- **📚 RAG Pipeline** — ChromaDB vector store for policy/FAQ retrieval
- **💾 Stateful Memory** — Persistent conversation history with automatic summarization
- **🔄 Multi-Step Workflows** — Complex operations like refund-with-notification chains
- **🆘 Smart Escalation** — Context-aware handoff to human agents
- **🔒 Production Patterns** — Connection pooling, input validation, ownership checks

---

## 🧠 Agent Architecture

The system uses a **graph-based agent orchestration** pattern where each node is a specialized agent:

```
User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│  SESSION MANAGER                                            │
│  • Load conversation history                                │
│  • Inject customer context                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  INTENT CLASSIFIER                                          │
│  • Detect user intent (track, cancel, refund, policy, etc) │
│  • Extract entities (order_id, customer_id, products)      │
│  • Validate completeness                                    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  DECISION ROUTER (Conditional Edges)                        │
│  • Route to appropriate agent based on intent               │
└─────────────────────────────────────────────────────────────┘
    ↓
    ├─→ ACTION AGENT (Write Operations)
    │   • Tool calling for cancel_order, process_refund, modify_order
    │   • Automatic email notifications
    │   • Ownership validation
    │
    ├─→ TOOL AGENT (Read Operations)
    │   • Database queries: track order, order history, account status
    │   • Drug catalog search
    │
    ├─→ RAG AGENT (Knowledge Retrieval)
    │   • Vector similarity search in ChromaDB
    │   • Policy/FAQ retrieval
    │
    ├─→ CLARIFICATION AGENT
    │   • Handle missing entities
    │   • Request additional information
    │
    └─→ ESCALATION AGENT
        • Package context for human handoff
        • Queue for supervisor review
    ↓
┌─────────────────────────────────────────────────────────────┐
│  RESPONSE GENERATOR                                         │
│  • Natural language generation from tool results/RAG        │
│  • Context-aware responses                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  MEMORY UPDATER                                             │
│  • Append turn to conversation history                      │
│  • Trigger summarization when needed                        │
│  • Log interaction metrics                                  │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

- **Modularity**: Each agent has a single responsibility
- **Scalability**: Easy to add new intents/agents without touching existing code
- **Observability**: Clear execution path for debugging
- **Flexibility**: Dynamic routing vs hardcoded if/else chains

---

## 🔄 Execution Flow Example

**User**: "Cancel my order ORD00001"

1. **Session Manager** loads conversation history for this user
2. **Intent Classifier** detects `cancel_order` intent, extracts `order_id: ORD00001`
3. **Decision Router** routes to **Action Agent** (write operation)
4. **Action Agent**:
   - Validates user owns this order
   - Calls `cancel_order` tool (LLM-driven tool selection)
   - Updates database: `order_status = 'cancelled'`
   - Automatically triggers `send_customer_email` tool
5. **Response Generator** creates natural language response
6. **Memory Updater** logs interaction, updates conversation history

**Result**: Order cancelled, email sent, interaction logged — all autonomous.

---

## ⚙️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | LangGraph | Multi-agent state machine with conditional routing |
| **LLM** | Groq (Llama 3.3 70B) | Intent classification, tool calling, response generation |
| **Vector DB** | ChromaDB | Semantic search for policy/FAQ retrieval |
| **Embeddings** | Sentence Transformers | all-MiniLM-L6-v2 for document encoding |
| **Database** | PostgreSQL | Customer/order data with connection pooling |
| **API** | FastAPI | RESTful endpoints with async support |
| **Frontend** | Next.js 14 + Streamlit | Dual UI options (modern web + rapid prototyping) |
| **Tools** | LangChain Tools | Database operations as LLM-callable functions |

---

## 💡 Real-World Use Cases

### 1. Order Cancellation with Auto-Notification
```
User: "Cancel order ORD00001"
System:
  → Validates ownership
  → Cancels order in database
  → Sends confirmation email automatically
  → Logs interaction for analytics
```

### 2. Multi-Step Refund Workflow
```
User: "I want a refund for ORD00002"
System:
  → Checks order status (must be cancelled/returned/shipped)
  → Initiates refund process
  → Updates order status to 'refund_initiated'
  → Notifies customer via email
  → Escalates to human if status invalid
```

### 3. Policy Questions (RAG)
```
User: "What's your return policy?"
System:
  → Retrieves relevant chunks from FAQ PDF
  → Generates answer grounded in retrieved context
  → No hallucination — answers only from knowledge base
```

### 4. Order Modification
```
User: "Change quantity to 2 for Paracetamol in ORD00003"
System:
  → Parses product update intent
  → Merges changes with existing order
  → Recalculates total amount
  → Updates database
  → Confirms changes to user
```

### 5. Context-Aware Escalation
```
User: "This is unacceptable, I want to speak to a manager"
System:
  → Detects escalation intent
  → Packages full conversation history
  → Includes customer profile + order details
  → Queues for human agent review
```

---

## 🏗️ Project Structure

```
backend/
├── agents/              # Specialized agents
│   ├── rag_agent.py        # ChromaDB retrieval
│   └── summary_agent.py    # Conversation summarization
├── api/
│   └── routes.py           # FastAPI endpoints
├── core/
│   ├── config.py           # Environment configuration
│   └── graph.py            # LangGraph pipeline builder
├── pipeline/nodes/      # Agent nodes
│   ├── intent/             # Intent classification + entity extraction
│   ├── decision/           # Routing logic
│   ├── action/             # Write operations (tool calling)
│   ├── rag/                # Knowledge retrieval
│   ├── response/           # NLG from tool results
│   ├── clarification/      # Missing entity recovery
│   └── system/             # Session, memory, escalation
├── state/
│   └── schema.py           # Shared state schema
├── tools/
│   └── db_tools.py         # LangChain @tool functions
└── main.py              # CLI entry point

frontend/                # Next.js UI
data/                    # Sample CSV data
rag/                     # RAG setup + PDF knowledge base
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, for full features)
- [Groq API Key](https://console.groq.com/keys) (free tier available)

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/pharma-assist-ai.git
cd pharma-assist-ai

# Create environment file
cp .env.example .env
# Add your Groq API key to .env
```

### 2. Install Dependencies
```bash
pip install -r requirements/base.txt
pip install -r requirements/api.txt
```

### 3. (Optional) Database Setup
```bash
# Create PostgreSQL database
createdb pharma_db

# Seed with sample data
python backend/scripts/seed.py
```

### 4. Run the System
```bash
# Option A: API Server
python start_server.py
# Access: http://localhost:8000/docs

# Option B: Streamlit UI
streamlit run backend/streamlit_app.py

# Option C: CLI
python -m backend.main
```

---

## 📊 Example API Usage

```bash
# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Track my order ORD00001",
    "session_id": "user123"
  }'

# Response
{
  "response": "Your order ORD00001 is currently shipped. Expected delivery: 2024-03-15.",
  "intent": "track_order",
  "confidence": 0.95
}
```

---

## 🎯 Supported Intents

| Intent | Agent Route | Example |
|--------|-------------|---------|
| `track_order` | Tool Agent | "Where is my order ORD00001?" |
| `cancel_order` | Action Agent | "Cancel order ORD00002" |
| `request_refund` | Action Agent | "I want a refund for ORD00003" |
| `modify_order` | Action Agent | "Change quantity to 2 in ORD00001" |
| `order_history` | Tool Agent | "Show my past orders" |
| `account_status` | Tool Agent | "What's my account status?" |
| `drug_search` | Tool Agent | "How much is Paracetamol?" |
| `check_policy` | RAG Agent | "What's your return policy?" |
| `escalate` | Escalation Agent | "I want to speak to a manager" |

---

## 🔒 Production-Ready Features

- ✅ **Connection Pooling**: 95% faster DB operations (2-10 pooled connections)
- ✅ **Input Sanitization**: SQL injection protection, length limits
- ✅ **Ownership Validation**: Users can only modify their own orders
- ✅ **Error Handling**: Graceful degradation when DB/LLM unavailable
- ✅ **Observability**: Structured logging at every node
- ✅ **CORS Configuration**: Restrict API access to trusted origins
- ✅ **Session Management**: Persistent state with LangGraph MemorySaver

---

## 📈 Performance Metrics

- **Average Response Time**: ~1.2s (including LLM inference)
- **Database Query Time**: ~55ms (with connection pooling)
- **RAG Retrieval**: ~200ms (3 chunks, cosine similarity)
- **Concurrent Users**: Tested with 10 simultaneous sessions
- **Uptime**: Designed for 24/7 operation with automatic reconnection

---

## 🚀 Future Enhancements

- [ ] **Async Processing**: Queue-based architecture for long-running operations
- [ ] **Caching Layer**: Redis for frequently accessed data
- [ ] **Monitoring**: Prometheus + Grafana for real-time metrics
- [ ] **A/B Testing**: Compare agent routing strategies
- [ ] **Multi-Language**: i18n support for global deployment
- [ ] **Voice Interface**: Real-time speech-to-speech pipeline
- [ ] **Fine-Tuning**: Custom intent classifier on domain data

---

## 🧪 Testing

```bash
# Run integration tests
python tests/test_db_tools.py

# Test agent pipeline
python -c "from backend.core.graph import build_graph; \
           g = build_graph(); \
           print(g.invoke({'user_input': 'Track ORD00001', 'session_id': 'test'}))"
```

---

## 📚 Key Learnings

Building this system taught me:

1. **Agent Design Patterns**: When to use tool calling vs RAG vs direct LLM generation
2. **State Management**: How to maintain context across multi-turn conversations
3. **Error Recovery**: Handling missing entities, invalid states, and LLM failures
4. **Production Considerations**: Connection pooling, input validation, observability
5. **LangGraph Orchestration**: Conditional routing, checkpointing, and state reducers

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional intent types (appointment booking, prescription refills)
- Enhanced RAG (reranking, hybrid search)
- Agent evaluation framework
- Load testing suite

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent orchestration
- [Groq](https://groq.com/) — Fast LLM inference
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework

---

**⭐ If this project demonstrates useful agentic AI patterns, please star the repo!**

*Built to showcase production-grade multi-agent systems for AI engineering roles.*
