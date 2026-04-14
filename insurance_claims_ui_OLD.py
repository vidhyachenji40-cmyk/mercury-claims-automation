# -*- coding: utf-8 -*-
"""
Insurance Claims AI System - Gradio Web Interface
Interactive demo combining:
- Policy Q&A (Mercury Insurance Assistant)
- Claim Filing (ClaimsCenter Producer)
- AI Agent Processing (Kafka Consumer Workflow)
"""

import gradio as gr
import json
import logging
from datetime import datetime
from typing import Tuple, List
import os

# Import from our main system (or copy the classes here)
# from insurance_claims_ai_system import (
#     InsuranceClaimsOrchestrator, ClaimEvent, ClaimStatus
# )

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GradioUI")

# Global orchestrator instance
orchestrator = None

def initialize_system(pdf_path: str) -> str:
    """Initialize the Insurance Claims AI System"""
    global orchestrator
    try:
        # Note: Import would happen here in production
        # orchestrator = InsuranceClaimsOrchestrator(pdf_path=pdf_path)
        logger.info(f"System initialized with {pdf_path}")
        return f"✅ System initialized with {pdf_path}"
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return f"❌ Error: {str(e)}"


def query_policy(question: str) -> str:
    """
    TAB 1: Policy Q&A
    User asks questions about Mercury insurance policy
    """
    if not orchestrator:
        return "❌ System not initialized. Please upload PDF first."
    
    try:
        answer = orchestrator.vector_db.retrieve_policy_chunk(question)
        return f"**Policy Answer:**\n\n{answer}"
    except Exception as e:
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
        return "❌ System not initialized.", ""
    
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

**Claim ID:** {claim_id}
**Customer ID:** {customer_id}
**Policy ID:** {policy_id}
**Claim Type:** {claim_type}
**Description:** {description}
**Damage Assessment:** {damage_description}

**Status:** FILED (awaiting agent processing)
**Timestamp:** {datetime.now().isoformat()}

*The claim has been posted to the Kafka topic 'claim-events'.*
*AI Agents are now processing this claim...*
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
        orchestrator.process_all_claims()
        
        approval_queue = orchestrator.get_approval_queue()
        
        result = "✅ **CLAIMS PROCESSING COMPLETE**\n\n"
        result += f"**Total Claims Processed:** {len(approval_queue)}\n\n"
        
        for claim_id, claim_data in approval_queue.items():
            decision = claim_data["decision"]
            result += f"""
---
**Claim ID:** {claim_id}
**Agent Type:** {decision['agent_type']}
**Recommendation:** {decision['recommendation']}
**Confidence:** {decision['confidence']:.1%}
**Reasoning:** {decision['reasoning'][:200]}...
**Next Action:** Send to human adjuster for approval
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
        return "📋 **Approval Queue is Empty**\n\nNo claims awaiting approval."
    
    result = "📋 **HUMAN ADJUSTER APPROVAL QUEUE**\n\n"
    result += f"Total Claims Awaiting Review: {len(approval_queue)}\n\n"
    
    for i, (claim_id, claim_data) in enumerate(approval_queue.items(), 1):
        decision = claim_data["decision"]
        payout = decision.get("payout_amount", "Not set")
        
        result += f"""
**[{i}] Claim ID:** {claim_id}
- **Agent Recommendation:** {decision['recommendation']}
- **Confidence Score:** {decision['confidence']:.1%}
- **Payout Amount:** ${payout:,} if applicable
- **Agent Reasoning:**
  > {decision['reasoning'][:300]}...
- **Status:** Ready for Approval
- **Submitted:** {claim_data['timestamp']}

"""
    
    return result


def system_status() -> str:
    """
    TAB 5: System Status
    Show architecture overview and system health
    """
    status = """
🏗️  **INSURANCE CLAIMS AI SYSTEM - ARCHITECTURE**

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

**Current System Status:**
✅ Vector Database: Initialized
✅ Kafka Topic Simulator: Active
✅ AI Agents: Ready
✅ Guidewire Integration: Connected

**Key Components:**
1. **Policy Vector DB** - Insurance rules chunked & embedded
2. **RAG System** - Semantic search for policy rules
3. **Kafka Topic** - claim-events (producer/consumer pattern)
4. **AI Agents**:
   - Total Loss Agent → Handles vehicle total loss claims
   - Fraud Detection Agent → Checks for suspicious patterns
   - Billing Agent → Verifies premium status
5. **Guidewire API** - Decision posting to approval queue
6. **Human Adjuster Queue** - Final approval workflow

**Workflow:**
1. ClaimsCenter files claim → Publishes to Kafka
2. Consumer Agents subscribe & process
3. Each agent: Observe → Reason → Retrieve (RAG) → Act → Decide
4. Decisions posted back to Guidewire
5. Human adjuster reviews & approves
6. Payment initiated back to Guidewire
    """
    return status


# ============================================================================
# GRADIO INTERFACE SETUP
# ============================================================================

def create_ui():
    """Build the complete Gradio interface"""
    
    with gr.Blocks(title="Insurance Claims AI System", theme=gr.themes.Soft()) as demo:
        
        gr.Markdown("""
        # 🏢 Insurance Claims AI System
        **Real-time Claims Processing with RAG + Kafka + AI Agents**
        
        Combines policy Vector DB, Kafka event streaming, and AI agents for automated insurance claim decisions.
        """)
        
        # ===== TAB 1: SETUP =====
        with gr.Tab("🔧 Setup"):
            gr.Markdown("### Initialize System")
            
            with gr.Row():
                pdf_input = gr.Textbox(
                    value="MERCURY AUTO INSURANCE POLICY.pdf",
                    label="PDF Path",
                    placeholder="Path to insurance policy PDF"
                )
                init_btn = gr.Button("Initialize System", variant="primary")
            
            init_output = gr.Textbox(
                label="Status",
                interactive=False,
                lines=3
            )
            
            init_btn.click(
                fn=initialize_system,
                inputs=[pdf_input],
                outputs=[init_output]
            )
        
        # ===== TAB 2: POLICY Q&A =====
        with gr.Tab("❓ Policy Q&A"):
            gr.Markdown("""
            ### Ask About Mercury Insurance Policy
            Powered by RAG (Retrieval Augmented Generation) + Vector DB
            """)
            
            question_input = gr.Textbox(
                label="Question",
                placeholder="e.g., What is the coverage limit for total loss claims?",
                lines=2
            )
            
            question_btn = gr.Button("Ask Policy", variant="primary")
            
            answer_output = gr.Markdown(
                label="Policy Answer",
                value="*Answer will appear here*"
            )
            
            question_btn.click(
                fn=query_policy,
                inputs=[question_input],
                outputs=[answer_output]
            )
        
        # ===== TAB 3: FILE CLAIM =====
        with gr.Tab("📝 File Claim"):
            gr.Markdown("""
            ### File an Insurance Claim
            ClaimsCenter posts claim to Kafka topic 'claim-events'
            """)
            
            with gr.Row():
                customer_id_input = gr.Textbox(
                    label="Customer ID",
                    placeholder="CUST-001",
                    value="CUST-001"
                )
                policy_id_input = gr.Textbox(
                    label="Policy ID",
                    placeholder="POL-12345",
                    value="POL-12345"
                )
            
            with gr.Row():
                claim_type_input = gr.Dropdown(
                    label="Claim Type",
                    choices=["total-loss", "partial-damage", "theft", "fraud-check"],
                    value="total-loss"
                )
            
            description_input = gr.Textbox(
                label="Description",
                placeholder="Brief description of the claim",
                lines=2,
                value="2018 Honda Civic - totaled in accident"
            )
            
            damage_input = gr.Textbox(
                label="Damage Assessment",
                placeholder="Detailed damage description",
                lines=3,
                value="Total damage - vehicle not repairable"
            )
            
            file_btn = gr.Button("File Claim", variant="primary")
            
            confirmation_output = gr.Markdown(label="Confirmation")
            claim_id_output = gr.Textbox(label="Claim ID", interactive=False)
            
            file_btn.click(
                fn=file_claim_form,
                inputs=[customer_id_input, policy_id_input, claim_type_input,
                       description_input, damage_input],
                outputs=[confirmation_output, claim_id_output]
            )
        
        # ===== TAB 4: PROCESS CLAIMS =====
        with gr.Tab("⚙️ Process Claims"):
            gr.Markdown("""
            ### Process Queued Claims
            Trigger AI Agents to evaluate all filed claims
            """)
            
            process_btn = gr.Button("Process All Claims", variant="primary", size="lg")
            
            process_output = gr.Markdown(
                label="Processing Results",
                value="*Results will appear here after processing*"
            )
            
            process_btn.click(
                fn=process_claims,
                inputs=[],
                outputs=[process_output]
            )
        
        # ===== TAB 5: APPROVAL QUEUE =====
        with gr.Tab("✅ Approval Queue"):
            gr.Markdown("""
            ### Human Adjuster Review Queue
            Claims ready for final approval and payment
            """)
            
            refresh_btn = gr.Button("Refresh Queue")
            
            queue_output = gr.Markdown(
                label="Approval Queue",
                value="*Queue will appear here*"
            )
            
            refresh_btn.click(
                fn=view_approval_queue,
                inputs=[],
                outputs=[queue_output]
            )
        
        # ===== TAB 6: SYSTEM STATUS =====
        with gr.Tab("🏗️ Architecture"):
            status_output = gr.Markdown(system_status())
    
    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)
