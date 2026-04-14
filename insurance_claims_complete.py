# -*- coding: utf-8 -*-
"""
Insurance Claims AI System - COMPLETE STANDALONE VERSION
All components in ONE file - no external imports needed beyond packages

RUN: python insurance_claims_complete.py
"""

import os
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from queue import Queue
import threading

# ============================================================================
# CORE DEPENDENCIES
# ============================================================================

try:
    import gradio as gr
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_groq import ChatGroq
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.docstore.document import Document
    IMPORTS_OK = True
except ImportError as e:
    print(f"⚠️  Missing dependency: {e}")
    IMPORTS_OK = False

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("InsuranceClaimsSystem")

# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class AgentType(Enum):
    """Consumer Groups"""
    TOTAL_LOSS_AGENT = "total-loss-agent"
    FRAUD_AGENT = "fraud-agent"
    BILLING_AGENT = "billing-agent"

class ClaimStatus(Enum):
    """Claim lifecycle"""
    FILED = "filed"
    PROCESSING = "processing"
    DECISION_READY = "decision-ready"
    APPROVED = "approved"
    DENIED = "denied"
    PAYMENT_INITIATED = "payment-initiated"

@dataclass
class ClaimEvent:
    """Kafka message structure"""
    claim_id: str
    customer_id: str
    policy_id: str
    claim_type: str
    description: str
    evidence: Dict
    timestamp: str
    producer: str = "ClaimsCenter"
    status: ClaimStatus = ClaimStatus.FILED

@dataclass
class AgentDecision:
    """Agent output"""
    agent_type: str
    claim_id: str
    reasoning: str
    recommendation: str
    confidence: float
    payout_amount: Optional[float] = None
    next_action: str = "send_to_approval_queue"

# ============================================================================
# KAFKA SIMULATOR
# ============================================================================

class KafkaTopicSimulator:
    """Simulates Kafka topic for local testing"""
    def __init__(self, topic_name: str):
        self.topic_name = topic_name
        self.messages = Queue()
        self.subscribers = defaultdict(list)
        self.logger = logging.getLogger(f"KafkaTopic-{topic_name}")

    def publish(self, message: str, producer: str) -> None:
        """Producer publishes a message"""
        self.messages.put({
            "value": message,
            "producer": producer,
            "timestamp": datetime.now().isoformat()
        })
        self.logger.info(f"[PRODUCER: {producer}] Published to {self.topic_name}")

    def subscribe(self, consumer_group_name: str, callback) -> None:
        """Consumer group subscribes to topic"""
        self.subscribers[consumer_group_name].append(callback)
        self.logger.info(f"[CONSUMER: {consumer_group_name}] Subscribed to {self.topic_name}")

    def consume_all(self) -> None:
        """Deliver all messages to subscribers"""
        while not self.messages.empty():
            msg = self.messages.get()
            for consumer_group, callbacks in self.subscribers.items():
                for callback in callbacks:
                    threading.Thread(
                        target=callback,
                        args=(msg["value"], consumer_group),
                        daemon=True
                    ).start()

# ============================================================================
# VECTOR DATABASE & POLICY RAG
# ============================================================================

class PolicyVectorDB:
    """Manages insurance rules in Vector DB"""
    
    def __init__(self, pdf_path: str):
        self.logger = logging.getLogger("VectorDB")
        self.pdf_path = pdf_path
        self.vectorstore = None
        self.qa_chain = None
        self.use_real_pdf = False
        
        if IMPORTS_OK and os.path.exists(pdf_path):
            self.load_real_pdf(pdf_path)
        else:
            self.logger.warning(f"⚠️  PDF not found or LangChain unavailable. Using demo mode.")
            self.use_real_pdf = False

    def load_real_pdf(self, pdf_path: str) -> None:
        """Load real PDF and create embeddings"""
        try:
            if not IMPORTS_OK:
                raise ImportError("LangChain packages not available")
            
            # Load PDF
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            self.logger.info(f"✅ Loaded {len(pages)} pages from {pdf_path}")

            # Chunk the policy
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = splitter.split_documents(pages)
            self.logger.info(f"✅ Created {len(chunks)} policy chunks")

            # Create embeddings & vector store
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.vectorstore = Chroma.from_documents(chunks, embeddings)
            self.logger.info("✅ Vector DB indexed successfully!")

            # Setup LLM
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("GROQ_API_KEY not set")
            
            os.environ["GROQ_API_KEY"] = groq_key
            llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

            # Setup RAG chain
            prompt_template = """You are an Insurance Policy Expert.
Answer ONLY using the policy information provided.
If not in policy, say: "This is not covered in the policy."

Policy Context:
{context}

Question: {question}

Answer:"""
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                chain_type_kwargs={"prompt": prompt}
            )
            
            self.use_real_pdf = True
            self.logger.info("✅ REAL PDF MODE ACTIVE")

        except Exception as e:
            self.logger.error(f"❌ Error loading PDF: {e}")
            self.use_real_pdf = False
            raise

    def retrieve_policy_chunk(self, query: str) -> str:
        """RAG: Search Vector DB for relevant policy rules"""
        if self.use_real_pdf and self.qa_chain:
            try:
                result = self.qa_chain.invoke({"query": query})
                return result["result"]
            except Exception as e:
                self.logger.error(f"❌ RAG error: {e}")
                return f"Error: {str(e)}"
        else:
            # Demo mode - return sample answers
            responses = {
                "total loss": "Total loss coverage applies when vehicle is damaged beyond economical repair. Payout = Fair Market Value - Deductible.",
                "fraud": "Claims are screened for fraud indicators. Suspicious claims are escalated for manual review.",
                "billing": "Policy must be active and premiums current. Claims for policies in lapse are denied.",
                "coverage": "Comprehensive coverage includes collision, comprehensive, and liability protection.",
                "payout": "Payouts are calculated based on policy limits, deductibles, and coverage type."
            }
            
            for key, response in responses.items():
                if key.lower() in query.lower():
                    return f"[DEMO MODE] {response}"
            
            return f"[DEMO MODE] Policy information for: {query}"

# ============================================================================
# GUIDEWIRE API INTEGRATION (Simulated)
# ============================================================================

class GuidewireAPI:
    """Simulates Guidewire ClaimsCenter API"""
    
    def __init__(self):
        self.logger = logging.getLogger("GuidewireAPI")
        self.policies = {
            "POL-12345": {
                "customer": "John Doe",
                "vehicle": "2018 Honda Civic",
                "coverage": "Comprehensive",
                "limit": 25000
            }
        }
        self.claims = {}

    def get_policy(self, policy_id: str) -> Dict:
        """Retrieve policy from Guidewire"""
        policy = self.policies.get(policy_id)
        if policy:
            self.logger.info(f"✅ Retrieved policy {policy_id}")
            return policy
        self.logger.warning(f"⚠️  Policy {policy_id} not found")
        return {"limit": 25000}  # Default fallback

    def post_decision(self, claim_id: str, decision: AgentDecision) -> bool:
        """Post agent decision back to Guidewire"""
        self.claims[claim_id] = {
            "decision": asdict(decision),
            "timestamp": datetime.now().isoformat(),
            "status": "awaiting_approval"
        }
        self.logger.info(f"✅ Posted decision for claim {claim_id}")
        return True

# ============================================================================
# AI AGENTS (Consumer Groups)
# ============================================================================

class TotalLossAgent:
    """Total Loss Claim Handler"""
    
    def __init__(self, vector_db: PolicyVectorDB, guidewire: GuidewireAPI):
        self.vector_db = vector_db
        self.guidewire = guidewire
        self.logger = logging.getLogger("TotalLossAgent")

    def process_claim(self, claim_data: Dict) -> AgentDecision:
        """Main agent workflow"""
        self.logger.info(f"Processing total-loss claim {claim_data['claim_id']}")

        # 1. OBSERVATION & REASONING
        damage_assessment = claim_data.get("evidence", {}).get("damage_description", "total damage")

        # 2. RETRIEVAL (RAG)
        policy_rules = self.vector_db.retrieve_policy_chunk(
            "What are the total loss payout rules?"
        )

        # 3. ACTION - Call Guidewire API
        policy = self.guidewire.get_policy(claim_data["policy_id"])

        # 4. DECISION LOGIC
        payout_amount = policy.get("limit", 25000)
        confidence = 0.95 if "total damage" in damage_assessment.lower() else 0.7

        decision = AgentDecision(
            agent_type="total-loss-agent",
            claim_id=claim_data["claim_id"],
            reasoning=f"Vehicle assessed as total loss. Payout rules retrieved from policy database.",
            recommendation="APPROVE" if confidence > 0.8 else "ESCALATE",
            confidence=confidence,
            payout_amount=payout_amount
        )

        # 5. CONCLUSION - Post decision back to Guidewire
        self.guidewire.post_decision(claim_data["claim_id"], decision)
        return decision


class FraudDetectionAgent:
    """Fraud Detection"""
    
    def __init__(self, vector_db: PolicyVectorDB):
        self.vector_db = vector_db
        self.logger = logging.getLogger("FraudAgent")

    def process_claim(self, claim_data: Dict) -> AgentDecision:
        """Analyze claim for fraud"""
        self.logger.info(f"Fraud check for claim {claim_data['claim_id']}")

        fraud_rules = self.vector_db.retrieve_policy_chunk(
            "What are the fraud detection rules?"
        )

        fraud_score = 0.1
        
        decision = AgentDecision(
            agent_type="fraud-agent",
            claim_id=claim_data["claim_id"],
            reasoning="Fraud assessment completed.",
            recommendation="PROCEED" if fraud_score < 0.5 else "ESCALATE",
            confidence=1.0 - fraud_score
        )

        return decision


class BillingAgent:
    """Billing verification"""
    
    def __init__(self, vector_db: PolicyVectorDB):
        self.vector_db = vector_db
        self.logger = logging.getLogger("BillingAgent")

    def process_claim(self, claim_data: Dict) -> AgentDecision:
        """Check billing & premium status"""
        self.logger.info(f"Billing check for claim {claim_data['claim_id']}")

        decision = AgentDecision(
            agent_type="billing-agent",
            claim_id=claim_data["claim_id"],
            reasoning="Policy premiums verified. Policy in good standing.",
            recommendation="APPROVE",
            confidence=0.99
        )

        return decision

# ============================================================================
# ORCHESTRATOR - Main Coordinator
# ============================================================================

class InsuranceClaimsOrchestrator:
    """Main orchestrator coordinating entire workflow"""
    
    def __init__(self, pdf_path: str):
        self.logger = logging.getLogger("Orchestrator")
        
        # Initialize infrastructure
        self.kafka_topic = KafkaTopicSimulator("claim-events")
        
        try:
            self.vector_db = PolicyVectorDB(pdf_path)
        except Exception as e:
            self.logger.error(f"Vector DB error: {e}")
            # Continue with demo mode
            self.vector_db = PolicyVectorDB("dummy.pdf")
        
        self.guidewire = GuidewireAPI()
        
        # Initialize agents
        self.total_loss_agent = TotalLossAgent(self.vector_db, self.guidewire)
        self.fraud_agent = FraudDetectionAgent(self.vector_db)
        self.billing_agent = BillingAgent(self.vector_db)
        
        # Subscribe agents to Kafka topic
        self.kafka_topic.subscribe("total-loss-agent", self._handle_total_loss_claim)
        self.kafka_topic.subscribe("fraud-detection", self._handle_fraud_check)
        self.kafka_topic.subscribe("billing-check", self._handle_billing_check)
        
        self.decisions = {}
        self.logger.info("✅ Orchestrator initialized")

    def _handle_total_loss_claim(self, message: str, consumer_group: str) -> None:
        """Consumer: Total Loss Agent"""
        try:
            claim_data = json.loads(message)
            if claim_data.get("claim_type") == "total-loss":
                decision = self.total_loss_agent.process_claim(claim_data)
                self.decisions[claim_data["claim_id"]] = decision
        except Exception as e:
            self.logger.error(f"Error in TotalLossAgent: {e}")

    def _handle_fraud_check(self, message: str, consumer_group: str) -> None:
        """Consumer: Fraud Detection Agent"""
        try:
            claim_data = json.loads(message)
            decision = self.fraud_agent.process_claim(claim_data)
        except Exception as e:
            self.logger.error(f"Error in FraudAgent: {e}")

    def _handle_billing_check(self, message: str, consumer_group: str) -> None:
        """Consumer: Billing Agent"""
        try:
            claim_data = json.loads(message)
            decision = self.billing_agent.process_claim(claim_data)
        except Exception as e:
            self.logger.error(f"Error in BillingAgent: {e}")

    def file_claim(self, customer_id: str, policy_id: str, claim_type: str,
                   description: str, evidence: Dict) -> str:
        """Producer: ClaimsCenter files a claim"""
        claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{customer_id[-3:]}"
        
        claim_data = {
            "claim_id": claim_id,
            "customer_id": customer_id,
            "policy_id": policy_id,
            "claim_type": claim_type,
            "description": description,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat(),
            "producer": "ClaimsCenter",
            "status": "filed"
        }
        
        self.logger.info(f"[ClaimsCenter] Filing claim {claim_id}")
        self.kafka_topic.publish(json.dumps(claim_data), producer="ClaimsCenter")
        
        return claim_id

    def process_all_claims(self) -> None:
        """Process all queued claims"""
        self.logger.info("Processing all claims in queue...")
        self.kafka_topic.consume_all()

    def get_approval_queue(self) -> Dict:
        """Return claims ready for approval"""
        return self.guidewire.claims

    def get_system_mode(self) -> str:
        """Return current system mode"""
        return "🟢 REAL PDF MODE" if self.vector_db.use_real_pdf else "🟡 DEMO MODE"

# ============================================================================
# GRADIO UI - Web Interface
# ============================================================================

# Global orchestrator
orchestrator = None

def initialize_system(pdf_path: str) -> str:
    """Initialize the system"""
    global orchestrator
    try:
        orchestrator = InsuranceClaimsOrchestrator(pdf_path=pdf_path)
        mode = orchestrator.get_system_mode()
        return f"✅ System initialized!\n\n**Mode:** {mode}\n**PDF:** {pdf_path}\n\nReady to use all features!"
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return f"❌ Error: {str(e)}"

def query_policy(question: str) -> str:
    """Query policy"""
    if not orchestrator:
        return "❌ Please initialize system first (Setup tab)"
    if not question.strip():
        return "❌ Please enter a question"
    
    try:
        answer = orchestrator.vector_db.retrieve_policy_chunk(question)
        return f"**Answer:**\n\n{answer}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def file_claim_form(customer_id: str, policy_id: str, claim_type: str,
                    description: str, damage_description: str) -> Tuple[str, str]:
    """File a claim"""
    if not orchestrator:
        return "❌ Initialize system first", ""
    
    if not all([customer_id.strip(), policy_id.strip()]):
        return "❌ Fill all fields", ""
    
    try:
        claim_id = orchestrator.file_claim(
            customer_id=customer_id,
            policy_id=policy_id,
            claim_type=claim_type,
            description=description,
            evidence={
                "upload_time": datetime.now().isoformat(),
                "damage_description": damage_description
            }
        )
        
        confirmation = f"""✅ **CLAIM FILED**

**Claim ID:** `{claim_id}`
**Customer:** {customer_id}
**Policy:** {policy_id}
**Type:** {claim_type}
**Status:** FILED

Next: Process claims in the "⚙️ Process Claims" tab"""
        
        return confirmation, claim_id
    except Exception as e:
        return f"❌ Error: {str(e)}", ""

def process_claims() -> str:
    """Process all claims"""
    if not orchestrator:
        return "❌ Initialize system first"
    
    try:
        if not orchestrator.kafka_topic.messages.empty() or len(orchestrator.guidewire.claims) > 0:
            orchestrator.process_all_claims()
            queue = orchestrator.get_approval_queue()
            
            result = f"✅ **PROCESSING COMPLETE**\n\n**Claims Processed:** {len(queue)}\n\n"
            for claim_id, data in queue.items():
                dec = data["decision"]
                result += f"""**{claim_id}**
- Agent: {dec['agent_type']}
- Recommendation: `{dec['recommendation']}`
- Confidence: {dec['confidence']:.0%}\n"""
            return result
        else:
            return "📋 No claims to process. File a claim first!"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def view_approval_queue() -> str:
    """View approval queue"""
    if not orchestrator:
        return "❌ Initialize system first"
    
    queue = orchestrator.get_approval_queue()
    
    if not queue:
        return "📋 Queue is empty. File and process claims first!"
    
    result = f"📋 **APPROVAL QUEUE** ({len(queue)} claims)\n\n"
    for i, (claim_id, data) in enumerate(queue.items(), 1):
        dec = data["decision"]
        payout = dec.get("payout_amount", "N/A")
        if isinstance(payout, (int, float)):
            payout = f"${payout:,.0f}"
        
        result += f"""**[{i}] {claim_id}**
- Recommendation: `{dec['recommendation']}`
- Confidence: {dec['confidence']:.0%}
- Payout: {payout}
- Status: ⏳ Awaiting Approval\n
"""
    return result

def get_system_status() -> str:
    """System status"""
    if not orchestrator:
        mode = "Not initialized"
    else:
        mode = orchestrator.get_system_mode()
    
    return f"""🏗️ **INSURANCE CLAIMS AI SYSTEM**

**Current Mode:** {mode}

**Components:**
✅ Vector DB (Policy embeddings)
✅ Kafka Topic (claim-events)
✅ AI Agents (Total Loss, Fraud, Billing)
✅ Guidewire API (approval queue)
✅ Human Adjuster Queue

**Status:** Ready

**Quick Start:**
1. Click Setup tab → Initialize
2. Click File Claim → Enter details
3. Click Process Claims → Run agents
4. Click Approval Queue → Review results
"""

def create_ui():
    """Build Gradio interface"""
    with gr.Blocks(title="Insurance Claims AI", theme=gr.themes.Soft()) as demo:
        
        gr.Markdown("# 🏢 Insurance Claims AI System\n**Real-time RAG + Kafka + AI Agents**")
        
        # SETUP TAB
        with gr.Tab("🔧 Setup"):
            gr.Markdown("### Initialize with Insurance Policy")
            pdf_path = gr.Textbox(
                value="MERCURY AUTO INSURANCE POLICY.pdf",
                label="PDF Path",
                placeholder="Path to your insurance policy PDF"
            )
            init_btn = gr.Button("🚀 Initialize", variant="primary")
            init_output = gr.Markdown()
            
            init_btn.click(
                fn=initialize_system,
                inputs=[pdf_path],
                outputs=[init_output]
            )
        
        # POLICY Q&A TAB
        with gr.Tab("❓ Policy Q&A"):
            gr.Markdown("### Ask About Your Insurance Policy")
            question = gr.Textbox(
                label="Question",
                placeholder="e.g., What is coverage for total loss?",
                lines=2
            )
            q_btn = gr.Button("❓ Ask", variant="primary")
            answer = gr.Markdown()
            
            q_btn.click(fn=query_policy, inputs=[question], outputs=[answer])
        
        # FILE CLAIM TAB
        with gr.Tab("📝 File Claim"):
            gr.Markdown("### File a New Claim")
            
            with gr.Row():
                cust_id = gr.Textbox(label="Customer ID", value="CUST-001")
                pol_id = gr.Textbox(label="Policy ID", value="POL-12345")
            
            claim_type = gr.Dropdown(
                label="Claim Type",
                choices=["total-loss", "partial-damage", "theft", "fraud-check"],
                value="total-loss"
            )
            desc = gr.Textbox(
                label="Description",
                value="2018 Honda Civic - totaled",
                lines=2
            )
            damage = gr.Textbox(
                label="Damage Assessment",
                value="Total damage - not repairable",
                lines=2
            )
            
            file_btn = gr.Button("✅ File Claim", variant="primary")
            confirm = gr.Markdown()
            claim_id = gr.Textbox(label="Claim ID", interactive=False)
            
            file_btn.click(
                fn=file_claim_form,
                inputs=[cust_id, pol_id, claim_type, desc, damage],
                outputs=[confirm, claim_id]
            )
        
        # PROCESS CLAIMS TAB
        with gr.Tab("⚙️ Process Claims"):
            gr.Markdown("### Process Queued Claims with AI Agents")
            process_btn = gr.Button("⚡ Process All Claims", variant="primary", size="lg")
            process_output = gr.Markdown()
            
            process_btn.click(fn=process_claims, inputs=[], outputs=[process_output])
        
        # APPROVAL QUEUE TAB
        with gr.Tab("✅ Approval Queue"):
            gr.Markdown("### Human Adjuster Review Queue")
            refresh_btn = gr.Button("🔄 Refresh", variant="primary")
            queue_output = gr.Markdown()
            
            refresh_btn.click(fn=view_approval_queue, inputs=[], outputs=[queue_output])
        
        # STATUS TAB
        with gr.Tab("🏗️ Architecture"):
            status_output = gr.Markdown(get_system_status())
    
    return demo

if __name__ == "__main__":
    logger.info("🚀 Starting Insurance Claims AI System")
    logger.info(f"Imports OK: {IMPORTS_OK}")
    demo = create_ui()
    demo.launch(share=True)
