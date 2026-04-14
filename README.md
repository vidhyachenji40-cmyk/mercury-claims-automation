# 🏢 Insurance Claims AI System

**Automated Insurance Claims Processing using RAG, Kafka, and AI Agents**

Combines your interview framework with the Mercury Insurance Assistant code to build a production-ready claims automation system.

---

## 📋 Overview

### Interview Framework (Your Foundation)
```
PRODUCER: ClaimsCenter
  ↓ (posts claim event)
KAFKA TOPIC: claim-events
  ↓ (message queue)
CONSUMERS: AI Agents (Total Loss, Fraud, Billing, Notifications)
  ↓ (read from topic)
VECTOR DB: Insurance Rules (chunked embeddings)
  ↓ (RAG: semantic search for policy rules)
ACTION: Call Guidewire API
  ↓
APPROVAL QUEUE: Human Adjuster Review
  ↓
PAYMENT: Initiate payout back to Guidewire
```

### The Total Loss Agent Workflow
```
1. OBSERVATION
   └─ Customer uploads photo of totaled car

2. REASONING
   └─ "This car looks beyond repair. I need policy rules."

3. RETRIEVAL (RAG)
   └─ Search Vector DB for payout rules for car model
   └─ Retrieve policy chunk from embeddings

4. ACTION
   └─ Call Guidewire API to fetch customer's policy
   └─ Extract coverage limit, deductible, etc.

5. CONCLUSION
   └─ Calculate payout amount
   └─ Post "Ready for Approval" to Kafka topic
   └─ Human adjuster reviews and approves
```

---

## 🏗️ Architecture

### Components

#### 1. **Vector Database (Policy Rules)**
- **What:** Insurance policy PDF split into 1000-char chunks with embeddings
- **Why:** Enable semantic search for policy rules
- **How:** LangChain + ChromaDB + HuggingFace embeddings
```python
# Example: Find total loss rules
policy_rules = vector_db.retrieve_policy_chunk(
    "What are total loss payout rules?"
)
```

#### 2. **Kafka Topic (Event Streaming)**
- **Topic Name:** `claim-events`
- **Producer:** ClaimsCenter (files claims)
- **Consumers:** AI Agents (process claims)
- **Message Format:** JSON ClaimEvent
```json
{
  "claim_id": "CLM-20240412120000-CUS",
  "customer_id": "CUST-001",
  "policy_id": "POL-12345",
  "claim_type": "total-loss",
  "description": "Totaled vehicle",
  "evidence": {
    "photo_url": "s3://...",
    "damage_description": "Total damage - not repairable"
  },
  "timestamp": "2024-04-12T12:00:00",
  "producer": "ClaimsCenter",
  "status": "filed"
}
```

#### 3. **AI Agents (Consumer Groups)**

**Total Loss Agent**
- Processes vehicle total loss claims
- Uses RAG to find payout rules
- Calls Guidewire API for policy details
- Posts decision to approval queue

**Fraud Detection Agent**
- Screens for suspicious patterns
- Retrieves fraud detection rules from Vector DB
- Recommends approval or escalation

**Billing Agent**
- Verifies premium payment status
- Ensures policy is active and in good standing

**Notification Agent**
- Sends updates to customer, adjuster, etc.

#### 4. **Guidewire API Integration**
```python
# Retrieve policy from ClaimsCenter
policy = guidewire.get_policy("POL-12345")

# Post decision back to approval queue
guidewire.post_decision(claim_id, decision)
```

#### 5. **Human Adjuster Approval Queue**
- Review AI agent recommendations
- Approve/deny claims
- Initiate payment processing

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install -q langchain langchain-community langchain-groq
pip install -q chromadb pypdf sentence-transformers
pip install -q gradio
pip install -q "numpy<2.0"
```

### Step 2: Prepare Your Policy PDF

Place your insurance policy in the working directory:
```
MERCURY AUTO INSURANCE POLICY.pdf
```

### Step 3: Set Environment Variables

```bash
export GROQ_API_KEY="your-groq-api-key"
```

### Step 4: Run the System

**Option A: Command-line processing**
```python
from insurance_claims_ai_system import InsuranceClaimsOrchestrator

# Initialize
orchestrator = InsuranceClaimsOrchestrator(
    pdf_path="MERCURY AUTO INSURANCE POLICY.pdf"
)

# File a claim
claim_id = orchestrator.file_claim(
    customer_id="CUST-001",
    policy_id="POL-12345",
    claim_type="total-loss",
    description="2018 Honda Civic - totaled in accident",
    evidence={
        "photo_url": "s3://claims-bucket/photo.jpg",
        "damage_description": "Total damage - not repairable"
    }
)

# Process claims
orchestrator.process_all_claims()

# View approval queue
queue = orchestrator.get_approval_queue()
orchestrator.print_summary()
```

**Option B: Web Interface**
```bash
python insurance_claims_ui.py
```

Then open: `http://localhost:7860`

---

## 📊 System Flow Example

### Scenario: Customer files total loss claim

```
1. FILE CLAIM (Producer: ClaimsCenter)
   Customer uploads damaged car photo
   → ClaimsCenter posts claim to Kafka topic "claim-events"
   
2. MESSAGE IN QUEUE
   ClaimEvent JSON:
   {
     claim_id: "CLM-20240412...",
     claim_type: "total-loss",
     evidence: { damage_description: "Total damage" }
   }
   
3. CONSUME & PROCESS (Agents subscribe)
   
   a) TOTAL LOSS AGENT:
      - Observation: Sees totaled vehicle photo
      - Reasoning: "Need to check Total Loss rules"
      - Retrieval (RAG): 
        Query: "What are total loss payout rules?"
        Result: "Total loss payout = Fair Market Value minus deductible"
      - Action: Call Guidewire API
        get_policy("POL-12345") → 
        { limit: $25,000, deductible: $500 }
      - Conclusion:
        Decision: APPROVE
        Payout: $24,500
        Post to Guidewire approval queue
   
   b) FRAUD AGENT:
      - Checks fraud patterns
      - Decision: PROCEED (low fraud risk)
   
   c) BILLING AGENT:
      - Verifies premium status
      - Decision: APPROVE (policy active)

4. APPROVAL QUEUE (Human Adjuster Review)
   Claim ID: CLM-20240412...
   Agent Recommendation: APPROVE
   Confidence: 95%
   Payout: $24,500
   → Adjuster reviews & signs off

5. PAYMENT INITIATED
   Guidewire processes payment
   Customer receives payout
```

---

## 🔑 Key Concepts

### RAG (Retrieval Augmented Generation)
1. **Chunking:** Break policy PDF into 1000-char sections with 200-char overlap
2. **Embedding:** Convert each chunk to vector (semantic meaning)
3. **Storage:** Store in ChromaDB Vector Database
4. **Retrieval:** When agent asks question, find most similar chunks
5. **Generation:** Use chunks as context for LLM response

Example:
```python
# Agent asks: "What are total loss rules?"
# System:
# 1. Convert question to embedding
# 2. Search Vector DB for similar chunks
# 3. Return top-5 policy chunks
# 4. Feed to LLM with prompt
# 5. LLM generates answer using policy context
```

### Kafka Consumer Pattern
```python
# Subscribe to topic
kafka_topic.subscribe("total-loss-agent", callback_function)

# When message arrives:
# callback_function(message) → processes claim → posts decision
```

### Agent Decision Flow
```
ClaimEvent → Agent.process_claim() → AgentDecision
  ├─ observation (what is happening?)
  ├─ reasoning (what do I need to know?)
  ├─ retrieval (RAG query to Vector DB)
  ├─ action (call Guidewire API)
  └─ conclusion (make decision + confidence)
```

---

## 🛠️ Customization

### Add New Agent Type

```python
class ClaimsDepartmentAgent:
    """Custom agent for specific claim type"""
    
    def __init__(self, vector_db, guidewire):
        self.vector_db = vector_db
        self.guidewire = guidewire
    
    def process_claim(self, claim: ClaimEvent) -> AgentDecision:
        # Your logic here
        policy_rules = self.vector_db.retrieve_policy_chunk(
            "Query for your claim type"
        )
        
        # Make decision
        return AgentDecision(
            agent_type=AgentType.YOUR_AGENT,
            claim_id=claim.claim_id,
            reasoning="...",
            recommendation="APPROVE",
            confidence=0.95
        )

# Register in orchestrator
orchestrator.kafka_topic.subscribe(
    "your-agent", 
    orchestrator._handle_your_agent_claim
)
```

### Connect Real Kafka

Replace `KafkaTopicSimulator` with `confluent-kafka`:

```python
from confluent_kafka import Producer, Consumer

# Producer
producer = Producer({'bootstrap.servers': 'localhost:9092'})
producer.produce('claim-events', value=claim.to_json())

# Consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'total-loss-agent'
})
consumer.subscribe(['claim-events'])

while True:
    msg = consumer.poll(1.0)
    if msg:
        claim = ClaimEvent.from_json(msg.value())
        agent.process_claim(claim)
```

### Connect Real Guidewire

Replace `GuidewireAPI` with REST calls:

```python
import requests

class GuidewireAPI:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_policy(self, policy_id: str) -> Dict:
        response = requests.get(
            f"{self.base_url}/api/policies/{policy_id}",
            headers={"Authorization": "Bearer YOUR_TOKEN"}
        )
        return response.json()
    
    def post_decision(self, claim_id: str, decision: AgentDecision) -> bool:
        response = requests.post(
            f"{self.base_url}/api/claims/{claim_id}/decision",
            json=asdict(decision),
            headers={"Authorization": "Bearer YOUR_TOKEN"}
        )
        return response.status_code == 200
```

---

## 📈 Production Checklist

- [ ] Replace Kafka simulator with real Kafka cluster
- [ ] Connect to production Guidewire ClaimsCenter API
- [ ] Add authentication/authorization to Guidewire API calls
- [ ] Implement audit logging for compliance
- [ ] Add monitoring & alerting (agent decision latency, approval rate, etc.)
- [ ] Setup human adjuster UI for approval queue
- [ ] Add payment processing integration
- [ ] Implement claim status notifications (email, SMS)
- [ ] Add ML model for better fraud detection
- [ ] Test with production insurance policies
- [ ] Set up CI/CD pipeline
- [ ] Load test agents (1000+ claims/day)

---

## 📚 File Structure

```
insurance_claims_ai_system.py
├─ KafkaTopicSimulator (event streaming)
├─ PolicyVectorDB (RAG + Vector DB)
├─ GuidewireAPI (policy lookup + decision posting)
├─ TotalLossAgent (consumer: total loss claims)
├─ FraudDetectionAgent (consumer: fraud screening)
├─ BillingAgent (consumer: billing verification)
└─ InsuranceClaimsOrchestrator (orchestrates entire workflow)

insurance_claims_ui.py
├─ Setup tab (initialize system)
├─ Policy Q&A tab (query insurance rules)
├─ File Claim tab (ClaimsCenter producer)
├─ Process Claims tab (trigger agents)
├─ Approval Queue tab (human adjuster review)
└─ Architecture tab (system diagram)
```

---

## 🧠 LLM Models Used

- **Embeddings:** `all-MiniLM-L6-v2` (HuggingFace) - 384 dimensions
- **LLM:** `llama-3.3-70b-versatile` (Groq) - Fast inference
- **Vector Store:** ChromaDB - In-memory or persistent

---

## 🔐 Security Notes

- ✅ Never commit API keys → use environment variables
- ✅ Validate all Kafka messages before processing
- ✅ Audit log all agent decisions for compliance
- ✅ Encrypt sensitive data (policy numbers, PII)
- ✅ Use TLS for Guidewire API communication
- ✅ Implement rate limiting on Vector DB queries

---

## 🤝 Integration Points

### Incoming Data
- **Kafka Topic:** `claim-events` ← ClaimsCenter (producer)

### Outgoing Data
- **Guidewire API:** Agent decisions → approval queue
- **Email/SMS:** Notifications to customer/adjuster
- **Payment System:** Approved payouts

---

## 📞 Support

**Interview Question Answers:**

1. **Topic** = name of board
   - `claim-events` (Kafka Topic)

2. **Producer** = whoever posts note
   - `ClaimsCenter` (files claims)

3. **Consumer** = whoever reads note
   - `TotalLossAgent`, `FraudAgent`, `BillingAgent`, `NotificationAgent`

4. **Preparation** = chunked embeddings in Vector DB
   - Policy PDF → 1000-char chunks → embeddings → ChromaDB

5. **Claim Filed** = message to Kafka
   - ClaimEvent JSON posted to `claim-events` topic

6. **Consumption** = consumer group reads message
   - Agents subscribe via `KafkaTopicSimulator.subscribe()`

7. **Retrieval** = search Vector DB
   - Agent calls `vector_db.retrieve_policy_chunk(query)`

8. **Action** = send decision back to Guidewire
   - `guidewire.post_decision(claim_id, decision)`

---

## 🎯 Next Steps

1. **Test locally** with sample claims
2. **Connect real Kafka** cluster
3. **Integrate with Guidewire** ClaimsCenter
4. **Deploy agents** as microservices
5. **Monitor & optimize** agent performance
6. **Scale** to production volume

---

**Built for your interview with complete code, architecture, and production readiness.** 🚀
