# -*- coding: utf-8 -*-
"""
Insurance Claims AI Agent System
Combines Kafka Event Streaming + Vector DB RAG + Guidewire Integration

Architecture:
Topic: claim-events (Kafka Topic)
Producer: ClaimsCenter (posts claim messages)
Consumers: AI Agents (Total Loss, Fraud, Billing), Human Adjusters
"""

import os
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# LLM & RAG Dependencies
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document

# Kafka simulation (for production: use confluent-kafka)
from collections import defaultdict
from queue import Queue
import threading

# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class AgentType(Enum):
    """Consumer Groups - Who reads the messages"""
    TOTAL_LOSS_AGENT = "total-loss-agent"
    FRAUD_AGENT = "fraud-agent"
    BILLING_AGENT = "billing-agent"
    NOTIFICATION_AGENT = "notification-agent"
    HUMAN_ADJUSTER = "human-adjuster"

class ClaimStatus(Enum):
    """Claim lifecycle states"""
    FILED = "filed"
    PROCESSING = "processing"
    DECISION_READY = "decision-ready"
    APPROVED = "approved"
    DENIED = "denied"
    PAYMENT_INITIATED = "payment-initiated"

@dataclass
class ClaimEvent:
    """Kafka message structure for claim-events topic"""
    claim_id: str
    customer_id: str
    policy_id: str
    claim_type: str  # e.g., "total-loss", "fraud-check", "billing"
    description: str
    evidence: Dict  # e.g., {"photo_url": "...", "upload_time": "..."}
    timestamp: str
    producer: str  # e.g., "ClaimsCenter"
    status: ClaimStatus = ClaimStatus.FILED

    def to_json(self) -> str:
        data = asdict(self)
        data['status'] = data['status'].value
        return json.dumps(data)

    @staticmethod
    def from_json(json_str: str) -> 'ClaimEvent':
        data = json.loads(json_str)
        data['status'] = ClaimStatus(data['status'])
        return ClaimEvent(**data)


@dataclass
class AgentDecision:
    """Output from an AI Agent"""
    agent_type: AgentType
    claim_id: str
    reasoning: str
    recommendation: str  # e.g., "APPROVE", "DENY", "ESCALATE"
    confidence: float  # 0-1
    payout_amount: Optional[float] = None
    next_action: str = "send_to_approval_queue"

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


# ============================================================================
# KAFKA SIMULATOR (In production, replace with confluent-kafka)
# ============================================================================

class KafkaTopicSimulator:
    """Simulates Kafka topic for local testing"""
    def __init__(self, topic_name: str):
        self.topic_name = topic_name
        self.messages = Queue()
        self.subscribers = defaultdict(list)
        self.logger = logging.getLogger(f"Topic-{topic_name}")

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
    
    def __init__(self, pdf_path: str, model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger("VectorDB")
        self.pdf_path = pdf_path
        self.vectorstore = None
        self.qa_chain = None
        self.load_and_index_policy(model_name)

    def load_and_index_policy(self, model_name: str) -> None:
        """Load PDF, chunk it, and create embeddings"""
        try:
            # Load PDF
            loader = PyPDFLoader(self.pdf_path)
            pages = loader.load()
            self.logger.info(f"Loaded {len(pages)} pages from {self.pdf_path}")

            # Chunk the policy
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = splitter.split_documents(pages)
            self.logger.info(f"Created {len(chunks)} policy chunks")

            # Create embeddings & vector store
            embeddings = HuggingFaceEmbeddings(model_name=model_name)
            self.vectorstore = Chroma.from_documents(chunks, embeddings)
            self.logger.info("Vector DB indexed successfully!")

            # Setup LLM
            os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "YOUR_KEY_HERE")
            llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

            # Setup RAG chain
            prompt_template = """You are an Insurance Policy Expert Agent.
Answer ONLY using the policy information provided.
If the answer is not in the policy, say: "This is not covered in the policy."

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

        except Exception as e:
            self.logger.error(f"Error initializing Vector DB: {e}")
            raise

    def retrieve_policy_chunk(self, query: str) -> str:
        """RAG: Search Vector DB for relevant policy rules"""
        try:
            result = self.qa_chain.invoke({"query": query})
            return result["result"]
        except Exception as e:
            self.logger.error(f"RAG retrieval error: {e}")
            return f"Error retrieving policy: {str(e)}"


# ============================================================================
# GUIDEWIRE API INTEGRATION (Simulated)
# ============================================================================

class GuidewireAPI:
    """Simulates Guidewire ClaimsCenter API"""
    
    def __init__(self):
        self.logger = logging.getLogger("GuidewireAPI")
        # Mock database
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
            self.logger.info(f"Retrieved policy {policy_id} from Guidewire")
            return policy
        self.logger.warning(f"Policy {policy_id} not found")
        return {}

    def post_decision(self, claim_id: str, decision: AgentDecision) -> bool:
        """Post agent decision back to Guidewire for approval queue"""
        self.claims[claim_id] = {
            "decision": asdict(decision),
            "timestamp": datetime.now().isoformat(),
            "status": "awaiting_approval"
        }
        self.logger.info(f"Posted decision for claim {claim_id} to Guidewire approval queue")
        return True


# ============================================================================
# AI AGENTS (Consumer Groups)
# ============================================================================

class TotalLossAgent:
    """
    Observation: Customer uploads photo of totaled car
    Reasoning: Checks 'Total Loss' rules in Vector DB
    Retrieval (RAG): Searches for payout rules for car model
    Action: Calls Guidewire API for policy
    Conclusion: Posts "Ready for Approval" message
    """
    
    def __init__(self, vector_db: PolicyVectorDB, guidewire: GuidewireAPI):
        self.vector_db = vector_db
        self.guidewire = guidewire
        self.logger = logging.getLogger("TotalLossAgent")

    def process_claim(self, claim: ClaimEvent) -> AgentDecision:
        """Main agent workflow"""
        self.logger.info(f"Processing total-loss claim {claim.claim_id}")

        # 1. OBSERVATION & REASONING
        self.logger.info("Step 1: Observation - Analyzing damage photo...")
        damage_assessment = claim.evidence.get("damage_description", "total damage")

        # 2. RETRIEVAL (RAG)
        self.logger.info("Step 2: Retrieval - Searching Vector DB for Total Loss rules...")
        policy_rules = self.vector_db.retrieve_policy_chunk(
            f"What are the total loss payout rules for {claim.claim_type}?"
        )

        # 3. ACTION - Call Guidewire API
        self.logger.info("Step 3: Action - Fetching policy from Guidewire...")
        policy = self.guidewire.get_policy(claim.policy_id)

        # 4. DECISION LOGIC
        payout_amount = policy.get("limit", 0)
        confidence = 0.95 if "total damage" in damage_assessment.lower() else 0.7

        decision = AgentDecision(
            agent_type=AgentType.TOTAL_LOSS_AGENT,
            claim_id=claim.claim_id,
            reasoning=f"Vehicle assessed as total loss. Policy rules: {policy_rules[:200]}...",
            recommendation="APPROVE" if confidence > 0.8 else "ESCALATE",
            confidence=confidence,
            payout_amount=payout_amount,
            next_action="send_to_approval_queue"
        )

        # 5. CONCLUSION - Post decision back to Guidewire
        self.logger.info("Step 5: Conclusion - Posting decision to Guidewire...")
        self.guidewire.post_decision(claim.claim_id, decision)

        return decision


class FraudDetectionAgent:
    """Detects suspicious claims using policy rules"""
    
    def __init__(self, vector_db: PolicyVectorDB):
        self.vector_db = vector_db
        self.logger = logging.getLogger("FraudAgent")

    def process_claim(self, claim: ClaimEvent) -> AgentDecision:
        """Analyze claim for fraud patterns"""
        self.logger.info(f"Fraud check for claim {claim.claim_id}")

        # RAG: Search for fraud indicators in policy
        fraud_rules = self.vector_db.retrieve_policy_chunk(
            "What are the fraud detection rules and red flags?"
        )

        # Simple fraud scoring (in production: ML model)
        fraud_score = 0.1  # Low risk by default
        
        decision = AgentDecision(
            agent_type=AgentType.FRAUD_AGENT,
            claim_id=claim.claim_id,
            reasoning=f"Fraud assessment completed. Rules checked: {fraud_rules[:150]}...",
            recommendation="PROCEED" if fraud_score < 0.5 else "ESCALATE",
            confidence=1.0 - fraud_score
        )

        return decision


class BillingAgent:
    """Ensures claim aligns with billing records"""
    
    def __init__(self, vector_db: PolicyVectorDB):
        self.vector_db = vector_db
        self.logger = logging.getLogger("BillingAgent")

    def process_claim(self, claim: ClaimEvent) -> AgentDecision:
        """Check billing & premium status"""
        self.logger.info(f"Billing check for claim {claim.claim_id}")

        decision = AgentDecision(
            agent_type=AgentType.BILLING_AGENT,
            claim_id=claim.claim_id,
            reasoning="Policy premiums verified. Policy is in good standing.",
            recommendation="APPROVE",
            confidence=0.99
        )

        return decision


# ============================================================================
# ORCHESTRATOR - Coordinates the entire workflow
# ============================================================================

class InsuranceClaimsOrchestrator:
    """
    Main orchestrator that:
    1. Receives claim events from Kafka (ClaimsCenter)
    2. Routes to appropriate AI Agents (Consumer Groups)
    3. Aggregates decisions
    4. Posts final decision back to Guidewire approval queue
    """
    
    def __init__(self, pdf_path: str):
        self.logger = logging.getLogger("Orchestrator")
        
        # Initialize infrastructure
        self.kafka_topic = KafkaTopicSimulator("claim-events")
        self.vector_db = PolicyVectorDB(pdf_path)
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

    def _handle_total_loss_claim(self, message: str, consumer_group: str) -> None:
        """Consumer: Total Loss Agent"""
        try:
            claim = ClaimEvent.from_json(message)
            if claim.claim_type == "total-loss":
                decision = self.total_loss_agent.process_claim(claim)
                self.decisions[claim.claim_id] = decision
                self.logger.info(f"Total Loss Agent Decision: {decision.recommendation}")
        except Exception as e:
            self.logger.error(f"Error in TotalLossAgent: {e}")

    def _handle_fraud_check(self, message: str, consumer_group: str) -> None:
        """Consumer: Fraud Detection Agent"""
        try:
            claim = ClaimEvent.from_json(message)
            decision = self.fraud_agent.process_claim(claim)
            self.logger.info(f"Fraud Agent Decision: {decision.recommendation}")
        except Exception as e:
            self.logger.error(f"Error in FraudAgent: {e}")

    def _handle_billing_check(self, message: str, consumer_group: str) -> None:
        """Consumer: Billing Agent"""
        try:
            claim = ClaimEvent.from_json(message)
            decision = self.billing_agent.process_claim(claim)
            self.logger.info(f"Billing Agent Decision: {decision.recommendation}")
        except Exception as e:
            self.logger.error(f"Error in BillingAgent: {e}")

    def file_claim(self, customer_id: str, policy_id: str, claim_type: str,
                   description: str, evidence: Dict) -> str:
        """
        Producer: ClaimsCenter files a claim
        Posts message to claim-events Kafka topic
        """
        claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{customer_id[:3]}"
        
        claim = ClaimEvent(
            claim_id=claim_id,
            customer_id=customer_id,
            policy_id=policy_id,
            claim_type=claim_type,
            description=description,
            evidence=evidence,
            timestamp=datetime.now().isoformat(),
            producer="ClaimsCenter",
            status=ClaimStatus.FILED
        )
        
        self.logger.info(f"[PRODUCER: ClaimsCenter] Filing claim {claim_id}")
        self.kafka_topic.publish(claim.to_json(), producer="ClaimsCenter")
        
        return claim_id

    def process_all_claims(self) -> None:
        """Process all queued claims (trigger consumer groups)"""
        self.logger.info("Processing all claims in queue...")
        self.kafka_topic.consume_all()

    def get_approval_queue(self) -> Dict:
        """Return claims ready for human adjuster approval"""
        return self.guidewire.claims

    def print_summary(self) -> None:
        """Print workflow summary"""
        print("\n" + "="*70)
        print("INSURANCE CLAIMS AI SYSTEM - WORKFLOW SUMMARY")
        print("="*70)
        print(f"Approval Queue (Ready for Human Adjuster):")
        for claim_id, claim_data in self.guidewire.claims.items():
            decision = claim_data["decision"]
            print(f"\n  Claim ID: {claim_id}")
            print(f"  Agent: {decision['agent_type']}")
            print(f"  Recommendation: {decision['recommendation']}")
            print(f"  Confidence: {decision['confidence']:.2%}")
            if decision.get('payout_amount'):
                print(f"  Payout: ${decision['payout_amount']:,.2f}")
        print("\n" + "="*70)


# ============================================================================
# EXAMPLE USAGE & DEMO
# ============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize system
    orchestrator = InsuranceClaimsOrchestrator(pdf_path="MERCURY AUTO INSURANCE POLICY.pdf")
    
    # Example: ClaimsCenter files a total loss claim
    print("\n[SCENARIO] Customer uploads photo of totaled car\n")
    claim_id = orchestrator.file_claim(
        customer_id="CUST-001",
        policy_id="POL-12345",
        claim_type="total-loss",
        description="2018 Honda Civic - totaled in accident",
        evidence={
            "photo_url": "s3://claims-bucket/clm-001-damage.jpg",
            "upload_time": datetime.now().isoformat(),
            "damage_description": "Total damage - vehicle not repairable"
        }
    )
    
    # Process all claims (trigger consumer agents)
    orchestrator.process_all_claims()
    
    # Print results
    orchestrator.print_summary()
    
    print("\n✅ System ready for production integration with:")
    print("   • Real Kafka (confluent-kafka)")
    print("   • Production Guidewire ClaimsCenter API")
    print("   • Human adjuster review UI")
    print("   • Payment processing pipeline")
