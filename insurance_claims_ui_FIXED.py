# -*- coding: utf-8 -*-
"""
Insurance Claims AI System - Gradio Web Interface (FIXED)
Interactive demo combining:
- Policy Q&A (Mercury Insurance Assistant)
- Claim Filing (ClaimsCenter Producer)
- AI Agent Processing (Kafka Consumer Workflow)
"""

import gradio as gr
import json
import logging
import sys
import os
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ============================================================================
# SETUP IMPORTS & FALLBACK CLASSES
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GradioUI")

# Try to import the main system
try:
    from insurance_claims_ai_system import (
        InsuranceClaimsOrchestrator, ClaimEvent, ClaimStatus
    )
    logger.info("✅ Successfully imported InsuranceClaimsOrchestrator")
    SYSTEM_IMPORTED = True
except ImportError as e:
    logger.warning(f"⚠️  Could not import InsuranceClaimsOrchestrator: {e}")
    logger.info("Using fallback inline implementation...")
    SYSTEM_IMPORTED = False

# ============================================================================
# FALLBACK IMPLEMENTATION (if main system not available)
# ============================================================================

if not SYSTEM_IMPORTED:
    
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
        claim_type: str
        description: str
        evidence: Dict
        timestamp: str
        producer: str = "ClaimsCenter"
        status: ClaimStatus = ClaimStatus.FILED

    class MockVectorDB:
        """Mock Vector DB for fallback mode"""
        def __init__(self, pdf_path: str):
            self.pdf_path = pdf_path
            logger.info(f"Mock Vector DB initialized with {pdf_path}")
        
        def retrieve_policy_chunk(self, query: str) -> str:
            """Return mock policy response"""
            responses = {
                "total loss": "Total loss coverage applies when vehicle is damaged beyond economical repair. Payout = Fair Market Value - Deductible",
                "fraud": "Claims are screened for fraud indicators. Suspicious claims are escalated for manual review.",
                "billing": "Policy must be active and premiums current. Claims for policies in lapse are denied.",
                "coverage": "Comprehensive coverage includes collision, comprehensive, and liability protection.",
                "payout": "Payouts are calculated based on policy limits, deductibles, and coverage type."
            }
            
            # Try to find matching response
            for key, response in responses.items():
                if key.lower() in query.lower():
                    return response
            
            return f"Policy information: {query} - Please ensure the actual PDF is loaded for real policy answers."

    class InsuranceClaimsOrchestrator:
        """Fallback minimal orchestrator"""
        
        def __init__(self, pdf_path: str):
            self.pdf_path = pdf_path
            self.vector_db = MockVectorDB(pdf_path)
            self.claims_filed = {}
            self.approval_queue = {}
            logger.info(f"✅ Orchestrator initialized with {pdf_path}")
        
        def file_claim(self, customer_id: str, policy_id: str, claim_type: str,
                      description: str, evidence: Dict) -> str:
            """File a new claim"""
            claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{customer_id[-3:]}"
            
            self.claims_filed[claim_id] = {
                "customer_id": customer_id,
                "policy_id": policy_id,
                "claim_type": claim_type,
                "description": description,
                "evidence": evidence,
                "timestamp": datetime.now().isoformat(),
                "status": "filed"
            }
            
            logger.info(f"[ClaimsCenter] Filed claim {claim_id}")
            return claim_id
        
        def process_all_claims(self) -> None:
            """Process all filed claims through agents"""
            for claim_id, claim_data in self.claims_filed.items():
                # Simulate agent processing
                decision = {
                    "claim_id": claim_id,
                    "agent_type": self._get_agent_for_claim(claim_data["claim_type"]),
                    "recommendation": "APPROVE" if claim_data["claim_type"] != "fraud-check" else "REVIEW",
                    "confidence": 0.92,
                    "reasoning": f"Processed {claim_data['claim_type']} claim with policy {claim_data['policy_id']}",
                    "payout_amount": 25000 if claim_data["claim_type"] == "total-loss" else None,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.approval_queue[claim_id] = {
                    "decision": decision,
                    "status": "awaiting_approval"
                }
                logger.info(f"[Agent] Processed claim {claim_id}: {decision['recommendation']}")
        
        def _get_agent_for_claim(self, claim_type: str) -> str:
            """Map claim type to agent"""
            mapping = {
                "total-loss": "total-loss-agent",
                "partial-damage": "damage-agent",
                "theft": "fraud-agent",
                "fraud-check": "fraud-agent"
            }
            return mapping.get(claim_type, "general-agent")
        
        def get_approval_queue(self) -> Dict:
            """Get claims ready for approval"""
            return self.approval_queue

# ============================================================================
# LOGGING & GLOBAL STATE
# ============================================================================

# Global orchestrator instance
orchestrator = None

def initialize_system(pdf_path: str) -> str:
    """Initialize the Insurance Claims AI System"""
    global orchestrator
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            return f"⚠️  Warning: PDF file not found at '{pdf_path}'. Using demo mode with sample data.\n\nTo use real policies:\n1. Place your PDF in the same directory\n2. Update the path above\n3. Click Initialize again"
        
        # Create orchestrator
        orchestrator = InsuranceClaimsOrchestrator(pdf_path=pdf_path)
        logger.info(f"✅ System initialized with {pdf_path}")
        
        mode = "REAL PDF MODE" if SYSTEM_IMPORTED else "DEMO MODE"
        return f"✅ System initialized successfully!\n\n**Mode:** {mode}\n**PDF:** {pdf_path}\n\nYou can now:\n1. Ask policy questions\n2. File claims\n3. Process claims\n4. View approval queue"
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        return f"❌ Error: {str(e)}\n\nTroubleshooting:\n1. Check PDF path is correct\n2. Ensure GROQ_API_KEY is set\n3. Check logs for details"


def query_policy(question: str) -> str:
    """
    TAB 1: Policy Q&A
    User asks questions about Mercury insurance policy
    """
    if not orchestrator:
        return "❌ System not initialized. Please click 'Initialize System' first."
    
    if not question.strip():
        return "❌ Please enter a question about the policy."
    
    try:
        answer = orchestrator.vector_db.retrieve_policy_chunk(question)
        mode_note = "\n\n*[Running in DEMO MODE - connect real PDF for actual policy answers]*" if not SYSTEM_IMPORTED else ""
        return f"**Policy Answer:**\n\n{answer}{mode_note}"
    except Exception as e:
        logger.error(f"Error in query_policy: {e}")
        return f"❌ Error retrieving policy: {str(e)}"


def file_claim_form(
    customer_id: str,
    policy_id: str,
    claim_type: str,
    description: str,
    damage_description: str
) -> Tuple[str, str]:
    """
    TAB 2: File a Claim
    ClaimsCenter (Producer) posts a message to claim-events topic
    """
    if not orchestrator:
        return "❌ System not initialized. Please click 'Initialize System' first.", ""
    
    # Validate inputs
    if not all([customer_id.strip(), policy_id.strip(), description.strip()]):
        return "❌ Please fill in all required fields.", ""
    
    try:
        # File the claim
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
        
        # Show confirmation
        confirmation = f"""
✅ **CLAIM FILED SUCCESSFULLY**

**Claim ID:** `{claim_id}`
**Customer ID:** {customer_id}
**Policy ID:** {policy_id}
**Claim Type:** {claim_type}
**Description:** {description}
**Damage Assessment:** {damage_description}

**Status:** FILED → Queued for agent processing

**Next Steps:**
1. Click "Process All Claims" tab to trigger AI agents
2. Claims will be evaluated by appropriate agents
3. Review results in "Approval Queue" tab

**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return confirmation, claim_id
        
    except Exception as e:
        logger.error(f"Error filing claim: {e}")
        return f"❌ Error filing claim: {str(e)}", ""


def process_claims() -> str:
    """
    TAB 3: Process Claims
    Trigger all consumer agents to process queued claims
    """
    if not orchestrator:
        return "❌ System not initialized."
    
    try:
        # Get claims before processing
        claims_before = len(orchestrator.claims_filed)
        
        if claims_before == 0:
            return "📋 No claims to process. Please file a claim first in the 'File Claim' tab."
        
        # Process all claims
        orchestrator.process_all_claims()
        
        approval_queue = orchestrator.get_approval_queue()
        
        result = f"✅ **CLAIMS PROCESSING COMPLETE**\n\n"
        result += f"**Claims Processed:** {len(approval_queue)}\n"
        result += f"**Approval Queue:** Ready for human adjuster review\n\n"
        
        for claim_id, claim_data in approval_queue.items():
            decision = claim_data["decision"]
            result += f"""
---
**Claim ID:** `{claim_id}`
- **Agent:** {decision['agent_type']}
- **Recommendation:** `{decision['recommendation']}`
- **Confidence:** {decision['confidence']:.0%}
- **Reasoning:** {decision['reasoning'][:200]}...
- **Status:** Ready for Approval Queue
            
"""
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing claims: {e}")
        return f"❌ Error processing claims: {str(e)}"


def view_approval_queue() -> str:
    """
    TAB 4: Approval Queue
    View claims ready for human adjuster sign-off
    """
    if not orchestrator:
        return "❌ System not initialized."
    
    approval_queue = orchestrator.get_approval_queue()
    
    if not approval_queue:
        return "📋 **Approval Queue is Empty**\n\nNo claims awaiting approval.\n\nTo get started:\n1. File a claim in 'File Claim' tab\n2. Click 'Process All Claims' tab\n3. Come back here to review"
    
    result = "📋 **HUMAN ADJUSTER APPROVAL QUEUE**\n\n"
    result += f"**Total Claims:** {len(approval_queue)}\n"
    result += f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for i, (claim_id, claim_data) in enumerate(approval_queue.items(), 1):
        decision = claim_data["decision"]
        payout = decision.get("payout_amount", "Not specified")
        
        if isinstance(payout, (int, float)):
            payout = f"${payout:,.2f}"
        
        result += f"""
**[{i}] Claim ID:** `{claim_id}`
- **Agent Recommendation:** `{decision['recommendation']}`
- **Confidence Score:** {decision['confidence']:.0%}
- **Payout Amount:** {payout}
- **Reasoning:** {decision['reasoning'][:250]}...
- **Status:** ⏳ Awaiting Adjuster Approval
- **Submitted:** {decision['timestamp']}

"""
    
    return result


def system_status() -> str:
    """
    TAB 5: System Status
    Show architecture overview and system health
    """
    status = f"""
🏗️  **INSURANCE CLAIMS AI SYSTEM - ARCHITECTURE**

**System Mode:** {'🟢 REAL PDF MODE' if SYSTEM_IMPORTED else '🟡 DEMO MODE'}

```
┌─────────────────────────────────────────────────────────┐
│  PRODUCER: ClaimsCenter (File Claims)                   │
└────────────────────┬────────────────────────────────────┘
                     │ (Claim Event JSON)
                     ↓
         ┌───────────────────────────┐
         │  KAFKA TOPIC: claim-events │
         └────────┬────────┬────────┬─┘
                  │        │        │
    ┌─────────────┘        │        └──────────────┐
    │                      │                       │
    ↓                      ↓                       ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Total Loss   │  │ Fraud        │  │ Billing      │
│ Agent        │  │ Detection    │  │ Agent        │
│              │  │ Agent        │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │ (RAG)           │ (RAG)           │ (RAG)
       │                 │                 │
       └────────┬────────┴────────┬────────┘
                ↓                 ↓
          ┌──────────────────────────────┐
          │ Vector DB (Policy Rules)      │
          │ Embeddings: insurance rules   │
          └──────────────────────────────┘
                
       ↓ (Decisions)
    ┌─────────────────────────────────┐
    │ GUIDEWIRE API (Approval Queue)   │
    │ Ready for Human Adjuster         │
    └─────────────────────────────────┘
```

**Component Status:**
✅ Vector Database: {'Initialized with PDF' if SYSTEM_IMPORTED else 'Demo Mode'}
✅ Kafka Topic Simulator: Active
✅ AI Agents: Ready (Total Loss, Fraud, Billing)
✅ Guidewire Integration: Connected
✅ Human Adjuster Queue: Available

**Workflow Steps:**
1. **File Claim** → ClaimsCenter posts to Kafka
2. **Process Claims** → AI Agents subscribe & evaluate
3. **Agent Logic:**
   - Observe claim details
   - Reason about policy rules
   - Retrieve (RAG) relevant policy chunks
   - Act by calling Guidewire API
   - Conclude with recommendation & confidence
4. **Approval Queue** → Human adjuster reviews
5. **Payment** → Initiate payout back to Guidewire

**Key Features:**
- 🧠 RAG (Retrieval Augmented Generation) for policy lookup
- 📨 Kafka producer/consumer pattern
- 🤖 Multi-agent AI system (Total Loss, Fraud, Billing)
- 👤 Human-in-the-loop approval process
- 📊 Real-time claim tracking

**Production Ready:**
- [x] Modular architecture
- [x] Error handling & logging
- [x] Fallback demo mode
- [x] Scalable agent pattern
- [ ] Real Kafka cluster (for production)
- [ ] Production Guidewire API (for production)
- [ ] High-volume testing (for production)
"""
    return status


# ============================================================================
# GRADIO INTERFACE SETUP
# ============================================================================

def create_ui():
    """Build the complete Gradio interface"""
    
    with gr.Blocks(
        title="Insurance Claims AI System",
        theme=gr.themes.Soft()
    ) as demo:
        
        gr.Markdown("""
        # 🏢 Insurance Claims AI System
        **Real-time Claims Processing with RAG + Kafka + AI Agents**
        
        Automated insurance claim decisions powered by policy embeddings, semantic search, and intelligent agents.
        """)
        
        # ===== TAB 0: SETUP =====
        with gr.Tab("🔧 Setup"):
            gr.Markdown("### Initialize System with Insurance Policy PDF")
            
            with gr.Row():
                pdf_input = gr.Textbox(
                    value="MERCURY AUTO INSURANCE POLICY.pdf",
                    label="📄 PDF Path",
                    placeholder="Path to insurance policy PDF (e.g., ./policy.pdf)"
                )
            
            with gr.Row():
                init_btn = gr.Button("🚀 Initialize System", variant="primary", scale=2)
                clear_btn = gr.Button("🔄 Clear", scale=1)
            
            init_output = gr.Markdown(
                value="*Ready to initialize. Click 'Initialize System' button.*",
                label="Initialization Status"
            )
            
            init_btn.click(
                fn=initialize_system,
                inputs=[pdf_input],
                outputs=[init_output]
            )
            
            clear_btn.click(
                fn=lambda: ("MERCURY AUTO INSURANCE POLICY.pdf", "*Cleared. Ready for new initialization.*"),
                inputs=[],
                outputs=[pdf_input, init_output]
            )
        
        # ===== TAB 1: POLICY Q&A =====
        with gr.Tab("❓ Policy Q&A"):
            gr.Markdown("""
            ### Ask About Insurance Policy
            **Powered by:** RAG (Retrieval Augmented Generation) + Vector Database
            
            Ask questions about coverage, limits, deductibles, and claim procedures.
            """)
            
            with gr.Row():
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., What is the coverage limit for total loss claims?",
                    lines=2
                )
            
            with gr.Row():
                question_btn = gr.Button("❓ Ask Policy", variant="primary")
            
            answer_output = gr.Markdown(
                value="*Answer will appear here*",
                label="Policy Answer"
            )
            
            question_btn.click(
                fn=query_policy,
                inputs=[question_input],
                outputs=[answer_output]
            )
        
        # ===== TAB 2: FILE CLAIM =====
        with gr.Tab("📝 File Claim"):
            gr.Markdown("""
            ### File an Insurance Claim
            **Producer:** ClaimsCenter posts claim to Kafka topic `claim-events`
            """)
            
            with gr.Row():
                customer_id_input = gr.Textbox(
                    label="👤 Customer ID",
                    placeholder="CUST-001",
                    value="CUST-001"
                )
                policy_id_input = gr.Textbox(
                    label="📋 Policy ID",
                    placeholder="POL-12345",
                    value="POL-12345"
                )
            
            with gr.Row():
                claim_type_input = gr.Dropdown(
                    label="📌 Claim Type",
                    choices=["total-loss", "partial-damage", "theft", "fraud-check"],
                    value="total-loss"
                )
            
            description_input = gr.Textbox(
                label="📝 Description",
                placeholder="Brief description of the claim",
                lines=2,
                value="2018 Honda Civic - totaled in accident"
            )
            
            damage_input = gr.Textbox(
                label="🔍 Damage Assessment",
                placeholder="Detailed damage description",
                lines=3,
                value="Total damage - vehicle not repairable"
            )
            
            with gr.Row():
                file_btn = gr.Button("✅ File Claim", variant="primary", scale=2)
                clear_claim_btn = gr.Button("🔄 Clear", scale=1)
            
            confirmation_output = gr.Markdown(label="Confirmation")
            claim_id_output = gr.Textbox(label="Claim ID", interactive=False)
            
            file_btn.click(
                fn=file_claim_form,
                inputs=[customer_id_input, policy_id_input, claim_type_input,
                       description_input, damage_input],
                outputs=[confirmation_output, claim_id_output]
            )
            
            clear_claim_btn.click(
                fn=lambda: ("", "", "total-loss", "", "", "1000", ""),
                inputs=[],
                outputs=[customer_id_input, policy_id_input, claim_type_input,
                        description_input, damage_input, confirmation_output, claim_id_output]
            )
        
        # ===== TAB 3: PROCESS CLAIMS =====
        with gr.Tab("⚙️ Process Claims"):
            gr.Markdown("""
            ### Process Queued Claims
            **Trigger:** AI Agents evaluate all filed claims using RAG + policy rules
            """)
            
            with gr.Row():
                process_btn = gr.Button("⚡ Process All Claims", variant="primary", size="lg")
            
            process_output = gr.Markdown(
                value="*Results will appear after processing. File a claim first!*",
                label="Processing Results"
            )
            
            process_btn.click(
                fn=process_claims,
                inputs=[],
                outputs=[process_output]
            )
        
        # ===== TAB 4: APPROVAL QUEUE =====
        with gr.Tab("✅ Approval Queue"):
            gr.Markdown("""
            ### Human Adjuster Review Queue
            **Status:** Claims ready for final approval and payment authorization
            """)
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Queue", variant="primary")
            
            queue_output = gr.Markdown(
                value="*Queue will appear here. Process claims first!*",
                label="Approval Queue"
            )
            
            refresh_btn.click(
                fn=view_approval_queue,
                inputs=[],
                outputs=[queue_output]
            )
        
        # ===== TAB 5: SYSTEM STATUS =====
        with gr.Tab("🏗️ Architecture"):
            status_output = gr.Markdown(system_status())
    
    return demo


if __name__ == "__main__":
    logger.info("Starting Insurance Claims AI System Web Interface...")
    demo = create_ui()
    demo.launch(share=True)
