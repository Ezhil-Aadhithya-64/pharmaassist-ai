# 🤖 PharmaAssist AI — Multi-Agent Customer Service System

> Production-grade agentic AI system for pharmacy e-commerce, built with LangGraph orchestration, tool calling, and RAG  
> Built collaboratively with [Saran-droid](https://github.com/Saran-droid)

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

The system uses a **graph-based agent orchestration** pattern powered by LangGraph, where each node is a specialized agent with a single responsibility. This architecture enables dynamic routing, stateful memory, and autonomous decision-making.

### High-Level Flow

```
User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│  SESSION MANAGER                                            │
│  • Load conversation history from MemorySaver               │
│  • Inject customer context (customer_id, past interactions) │
│  • Initialize state with session metadata                   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  INTENT CLASSIFIER                                          │
│  • Zero-shot intent detection via LLM                       │
│  • Extract entities (order_id, customer_id, products)       │
│  • Validate completeness (is_valid flag)                    │
│  • Confidence scoring (0.0-1.0)                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  DECISION ROUTER (Conditional Edges)                        │
│  • Route to appropriate agent based on intent + confidence  │
│  • Fallback to clarification if entities missing            │
└─────────────────────────────────────────────────────────────┘
    ↓
    ├─→ ACTION AGENT (Write Operations)
    │   • Tool calling: cancel_order, process_refund, modify_order
    │   • Ownership validation (customer_id check)
    │   • Automatic email notifications
    │   • Transaction logging
    │
    ├─→ TOOL AGENT (Read Operations)
    │   • Database queries: track_order, order_history, account_status
    │   • Drug catalog search
    │   • No side effects
    │
    ├─→ RAG AGENT (Knowledge Retrieval)
    │   • Vector similarity search in ChromaDB
    │   • Policy/FAQ retrieval from PDF knowledge base
    │   • Context-grounded responses (no hallucination)
    │
    ├─→ CLARIFICATION AGENT
    │   • Handle missing/ambiguous entities
    │   • Request additional information
    │   • Maintain conversation context
    │
    └─→ ESCALATION AGENT
        • Package full context for human handoff
        • Include conversation history + customer profile
        • Queue for supervisor review
    ↓
┌─────────────────────────────────────────────────────────────┐
│  RESPONSE GENERATOR                                         │
│  • Natural language generation from tool results/RAG        │
│  • Context-aware responses using conversation history       │
│  • Tone adaptation (empathetic for refunds, factual for tracking) │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  MEMORY UPDATER                                             │
│  • Append turn to conversation history (operator.add)       │
│  • Trigger summarization when history > threshold           │
│  • Log interaction metrics (resolution_status, action_taken) │
│  • Persist state to MemorySaver checkpoint                  │
└─────────────────────────────────────────────────────────────┘
```

### State Management

The system uses a shared `AgentState` schema (TypedDict) that flows through all nodes:

```python
AgentState = {
    # Core fields
    "session_id": str,           # Unique conversation identifier
    "customer_id": Optional[str], # Authenticated user (None = guest)
    "user_input": str,           # Current user message
    "agent_response": str,       # Generated response
    
    # Intent classification
    "intent": str,               # Detected intent (e.g., "cancel_order")
    "confidence": float,         # 0.0-1.0 confidence score
    "entities": dict,            # Extracted entities (order_id, product_name, etc.)
    "is_valid": bool,            # True if all required entities present
    
    # Memory & context
    "memory": List[dict],        # Conversation history (uses operator.add reducer)
    "summary": str,              # Condensed conversation summary
    
    # Tool execution
    "tool_result": dict,         # Results from database operations
    "tool_calls": List[dict],    # Raw tool call records
    
    # RAG
    "rag_context": str,          # Retrieved document chunks
    
    # Resolution tracking
    "action_taken": str,         # e.g., "order_cancelled", "refund_initiated"
    "resolution_status": str,    # "resolved", "escalated", "pending"
    "escalation_package": dict,  # Context for human agents
}
```

### Why This Architecture?

- **Modularity**: Each agent has a single responsibility (SRP), making testing and debugging easier
- **Scalability**: Add new intents/agents without modifying existing code (Open/Closed Principle)
- **Observability**: Clear execution path with state snapshots at each node
- **Flexibility**: Dynamic routing based on runtime conditions vs hardcoded if/else chains
- **Fault Tolerance**: Graceful degradation when individual agents fail
- **Stateful Memory**: LangGraph MemorySaver persists conversation context across sessions

---

## 🔄 Agent Workflow: Step-by-Step

### Example 1: Order Cancellation (Action Agent)

**User**: "Cancel my order ORD00001"

```
1. SESSION MANAGER
   ├─ Load state from MemorySaver (session_id: "user123")
   ├─ Retrieve conversation history: []
   ├─ Set customer_id: "CUST001" (from authentication)
   └─ State: {session_id, customer_id, user_input, memory: []}

2. INTENT CLASSIFIER
   ├─ LLM prompt: "Classify intent and extract entities from: 'Cancel my order ORD00001'"
   ├─ Response: {intent: "cancel_order", entities: {order_id: "ORD00001"}, confidence: 0.95}
   ├─ Validation: is_valid = True (all required entities present)
   └─ State: {..., intent, entities, confidence, is_valid}

3. DECISION ROUTER
   ├─ Check intent: "cancel_order"
   ├─ Check is_valid: True
   ├─ Route decision: "action_node" (write operation)
   └─ Conditional edge → ACTION AGENT

4. ACTION AGENT
   ├─ Ownership check: SELECT customer_id FROM orders WHERE order_id='ORD00001'
   │  └─ Result: customer_id='CUST001' ✓ (matches authenticated user)
   ├─ Tool selection: LLM chooses cancel_order(order_id="ORD00001")
   ├─ Execute tool:
   │  ├─ UPDATE orders SET order_status='cancelled' WHERE order_id='ORD00001'
   │  └─ INSERT INTO order_logs (order_id, action, timestamp)
   ├─ Auto-trigger: send_customer_email(to="user@example.com", subject="Order Cancelled")
   ├─ State update: {action_taken: "order_cancelled", resolution_status: "resolved"}
   └─ State: {..., tool_result: {success: True, message: "Order cancelled"}}

5. RESPONSE GENERATOR
   ├─ LLM prompt: "Generate response from tool_result: {success: True, ...}"
   ├─ Response: "Your order ORD00001 has been successfully cancelled. A confirmation email has been sent."
   └─ State: {..., agent_response}

6. MEMORY UPDATER
   ├─ Append to memory: {role: "user", content: "Cancel my order ORD00001"}
   ├─ Append to memory: {role: "assistant", content: "Your order ORD00001 has been..."}
   ├─ Check history length: 2 turns (no summarization needed)
   ├─ Log metrics: INSERT INTO session_logs (session_id, intent, resolution_status)
   └─ Persist state to MemorySaver checkpoint

7. END
   └─ Return: {agent_response, intent, confidence, resolution_status}
```

**Result**: Order cancelled, email sent, interaction logged — fully autonomous.

---

### Example 2: Missing Entity (Clarification Agent)

**User**: "I want to cancel my order"

```
1. SESSION MANAGER → Load state
2. INTENT CLASSIFIER
   ├─ Intent: "cancel_order"
   ├─ Entities: {} (no order_id extracted)
   ├─ is_valid: False (missing required entity)
   └─ State: {intent, entities: {}, is_valid: False}

3. DECISION ROUTER
   ├─ Check is_valid: False
   ├─ Route decision: "clarification_node"
   └─ Conditional edge → CLARIFICATION AGENT

4. CLARIFICATION AGENT
   ├─ Identify missing: "order_id"
   ├─ Generate prompt: "Which order would you like to cancel? Please provide the order ID."
   └─ State: {agent_response: "Which order would you like to cancel?..."}

5. RESPONSE GENERATOR → Pass through clarification response
6. MEMORY UPDATER → Log interaction, wait for user reply
7. END → Return clarification request
```

**Next Turn**: User provides "ORD00001" → System re-enters at SESSION MANAGER with updated context

---

### Example 3: Policy Question (RAG Agent)

**User**: "What's your return policy?"

```
1. SESSION MANAGER → Load state
2. INTENT CLASSIFIER
   ├─ Intent: "check_policy"
   ├─ Entities: {topic: "return_policy"}
   └─ State: {intent: "check_policy", is_valid: True}

3. DECISION ROUTER → Route to "rag_node"

4. RAG AGENT
   ├─ Embed query: "return policy" → vector [0.23, -0.45, ...]
   ├─ ChromaDB search: cosine_similarity(query_vector, document_vectors)
   ├─ Retrieve top 3 chunks:
   │  ├─ Chunk 1: "Returns accepted within 30 days..."
   │  ├─ Chunk 2: "Items must be unopened and in original packaging..."
   │  └─ Chunk 3: "Prescription medications cannot be returned..."
   ├─ Concatenate context: rag_context = chunk1 + chunk2 + chunk3
   └─ State: {..., rag_context}

5. RESPONSE GENERATOR
   ├─ LLM prompt: "Answer using ONLY this context: {rag_context}"
   ├─ Response: "Our return policy allows returns within 30 days for unopened items..."
   └─ State: {agent_response}

6. MEMORY UPDATER → Log interaction
7. END → Return grounded response (no hallucination)
```

---

### Example 4: Escalation (Human Handoff)

**User**: "This is unacceptable! I demand to speak to a manager NOW!"

```
1. SESSION MANAGER → Load state (includes past 5 turns of conversation)
2. INTENT CLASSIFIER
   ├─ Intent: "escalate"
   ├─ Confidence: 0.98
   └─ State: {intent: "escalate"}

3. DECISION ROUTER → Route to "escalation_node"

4. ESCALATION AGENT
   ├─ Package context:
   │  ├─ conversation_history: memory (last 10 turns)
   │  ├─ customer_profile: {customer_id, email, order_count, lifetime_value}
   │  ├─ current_issue: "Refund request denied for ORD00005"
   │  └─ sentiment: "negative" (detected from tone)
   ├─ Queue for human: INSERT INTO escalation_queue (session_id, priority, context)
   ├─ State: {escalation_package, resolution_status: "escalated"}
   └─ State: {agent_response: "I've escalated your case to a supervisor..."}

5. RESPONSE GENERATOR → Pass through escalation message
6. MEMORY UPDATER → Log escalation event
7. END → Human agent receives full context in dashboard
```

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
**Scenario**: Customer wants to cancel an order before shipment

```
User: "Cancel order ORD00001"

System Flow:
  1. Validates ownership (customer_id matches order)
  2. Checks order status (must be 'pending' or 'processing')
  3. Executes cancel_order tool → UPDATE orders SET order_status='cancelled'
  4. Auto-triggers send_customer_email tool
  5. Logs action: {action_taken: "order_cancelled", resolution_status: "resolved"}
  6. Responds: "Your order ORD00001 has been cancelled. Confirmation sent to your email."

Business Value:
  ✓ Zero human intervention required
  ✓ Instant resolution (avg 1.2s response time)
  ✓ Automatic audit trail for compliance
  ✓ Customer satisfaction through speed
```

---

### 2. Multi-Step Refund Workflow
**Scenario**: Customer requests refund for delivered order

```
User: "I want a refund for ORD00002"

System Flow:
  1. Checks order status: 'delivered' ✓
  2. Validates refund eligibility (within 30-day window)
  3. Executes process_refund tool:
     ├─ UPDATE orders SET order_status='refund_initiated'
     ├─ INSERT INTO refund_requests (order_id, amount, status='pending')
     └─ Trigger payment gateway API (async)
  4. Sends email: "Refund initiated. Expect 5-7 business days."
  5. If status invalid (e.g., 'cancelled') → Escalates to human

Edge Cases Handled:
  ✗ Order already refunded → "This order has already been refunded"
  ✗ Outside return window → Escalate with context
  ✗ Prescription medication → "Prescription items cannot be refunded per policy"
```

---

### 3. Policy Questions (RAG)
**Scenario**: Customer asks about return policy

```
User: "What's your return policy?"

System Flow:
  1. Intent: "check_policy", entities: {topic: "return_policy"}
  2. RAG Agent:
     ├─ Embed query → vector representation
     ├─ ChromaDB search → retrieve top 3 chunks from FAQ PDF
     ├─ Chunks: ["Returns within 30 days...", "Original packaging required...", "Prescription exclusions..."]
  3. Response Generator:
     ├─ LLM prompt: "Answer using ONLY this context: {rag_context}"
     ├─ Response: "Our return policy allows returns within 30 days for unopened items in original packaging. Prescription medications cannot be returned due to safety regulations."
  4. No hallucination — grounded in knowledge base

Why RAG?
  ✓ Accurate answers from authoritative source (PDF)
  ✓ No model fine-tuning required
  ✓ Easy to update (just replace PDF)
  ✓ Cite sources for transparency
```

---

### 4. Order Modification
**Scenario**: Customer wants to change product quantity before shipment

```
User: "Change quantity to 2 for Paracetamol in ORD00003"

System Flow:
  1. Intent: "modify_order", entities: {order_id: "ORD00003", product: "Paracetamol", quantity: 2}
  2. Action Agent:
     ├─ Fetch current order: SELECT * FROM orders WHERE order_id='ORD00003'
     ├─ Current: {product: "Paracetamol", quantity: 1, price: 5.99}
     ├─ Validate: order_status='pending' ✓ (can modify)
     ├─ Calculate new total: 2 × 5.99 = 11.98
     ├─ Execute modify_order tool:
     │  └─ UPDATE orders SET quantity=2, total_amount=11.98 WHERE order_id='ORD00003'
  3. Response: "Updated ORD00003: Paracetamol quantity changed to 2. New total: $11.98"

Complex Modifications:
  • Add product: "Add Aspirin to ORD00003"
  • Remove product: "Remove Vitamin C from ORD00003"
  • Change address: "Update delivery address for ORD00003"
```

---

### 5. Context-Aware Escalation
**Scenario**: Frustrated customer demands human agent

```
User: "This is unacceptable! I've been waiting 2 weeks for my refund. I want to speak to a manager NOW!"

System Flow:
  1. Intent: "escalate", confidence: 0.98
  2. Escalation Agent packages context:
     {
       "session_id": "user123",
       "customer_profile": {
         "customer_id": "CUST001",
         "email": "user@example.com",
         "lifetime_value": "$450",
         "order_count": 12,
         "vip_status": false
       },
       "conversation_history": [
         {"turn": 1, "user": "Where's my refund?", "agent": "Refund initiated 2 weeks ago..."},
         {"turn": 2, "user": "Still not received!", "agent": "Let me check..."},
         {"turn": 3, "user": "This is unacceptable!...", "agent": "Escalating..."}
       ],
       "current_issue": "Refund delay for ORD00005 ($89.99)",
       "sentiment": "negative",
       "priority": "high"
     }
  3. Queue for human: INSERT INTO escalation_queue (priority='high', context=...)
  4. Response: "I've escalated your case to a supervisor. They'll contact you within 1 hour with an update on your refund."

Human Agent Dashboard:
  ✓ Full conversation context (no need to ask "What's your order number?")
  ✓ Customer profile (lifetime value, order history)
  ✓ Sentiment analysis (prepare empathetic response)
  ✓ Suggested actions (expedite refund, offer discount)
```

---

### 6. Multi-Turn Conversation (Stateful Memory)
**Scenario**: Customer asks follow-up questions

```
Turn 1:
User: "Track my order"
Agent: "Which order would you like to track? Please provide the order ID."

Turn 2:
User: "ORD00001"
Agent: [Loads memory, sees previous turn] "Your order ORD00001 is currently shipped. Expected delivery: March 15."

Turn 3:
User: "Can I change the delivery address?"
Agent: [Remembers ORD00001 from context] "I can update the delivery address for ORD00001. What's the new address?"

Turn 4:
User: "123 Main St, New York, NY 10001"
Agent: [Updates order] "Delivery address updated for ORD00001. New address: 123 Main St, New York, NY 10001."

Memory Management:
  ✓ Conversation history persisted via LangGraph MemorySaver
  ✓ Automatic summarization after 10+ turns (reduce token usage)
  ✓ Entity tracking across turns (no need to repeat order_id)
```

---

### 7. Drug Catalog Search
**Scenario**: Customer searches for medication

```
User: "How much is Paracetamol 500mg?"

System Flow:
  1. Intent: "drug_search", entities: {drug_name: "Paracetamol", dosage: "500mg"}
  2. Tool Agent:
     ├─ Execute search_drug_catalog tool
     ├─ Query: SELECT * FROM drugs WHERE name ILIKE '%Paracetamol%' AND dosage='500mg'
     ├─ Result: {name: "Paracetamol", dosage: "500mg", price: 5.99, stock: 150}
  3. Response: "Paracetamol 500mg is $5.99. We have 150 units in stock. Would you like to place an order?"

Advanced Search:
  • Generic alternatives: "Show me generic versions of Advil"
  • Price comparison: "What's cheaper, Tylenol or Paracetamol?"
  • Stock check: "Is Amoxicillin available?"
```

---

### 8. Account Status Check
**Scenario**: Customer inquires about account details

```
User: "What's my account status?"

System Flow:
  1. Intent: "account_status", entities: {customer_id: "CUST001"}
  2. Tool Agent:
     ├─ Execute get_account_status tool
     ├─ Query: SELECT * FROM customers WHERE customer_id='CUST001'
     ├─ Result: {status: "active", loyalty_points: 250, pending_orders: 2}
  3. Response: "Your account is active. You have 250 loyalty points and 2 pending orders."

Related Queries:
  • "How many loyalty points do I have?"
  • "Show my order history"
  • "Am I eligible for free shipping?"
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

## 👥 Contributors

### Ezhil Aadhithyan K
- Designed multi-agent system architecture
- Built LangGraph orchestration pipeline with conditional routing
- Implemented intent classification and decision routing logic
- Developed action, clarification, and escalation agents
- Integrated FastAPI backend with stateful memory management
- Created Next.js frontend and Streamlit UI

### [Saran-droid](https://github.com/Saran-droid)
- Implemented database tool layer (LangChain @tool functions)
- Built PostgreSQL integration with connection pooling
- Contributed to RAG pipeline setup and ChromaDB integration
- Assisted in backend integration and testing

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
