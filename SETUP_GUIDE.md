# 🚀 Insurance Claims AI System - Setup Guide

## ✅ Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
# Install required packages
pip install -q langchain langchain-community langchain-groq
pip install -q chromadb pypdf sentence-transformers
pip install -q gradio
pip install "numpy<2.0"
```

### Step 2: Set API Key

```bash
# Set your Groq API key (get it from https://console.groq.com)
export GROQ_API_KEY="your-groq-api-key-here"
```

Or on Windows:
```cmd
set GROQ_API_KEY=your-groq-api-key-here
```

### Step 3: Run the UI

```bash
# Make sure both files are in the same directory:
# - insurance_claims_ai_system.py (the main system)
# - insurance_claims_ui_FIXED.py (the web interface)

python insurance_claims_ui_FIXED.py
```

Then open: **http://localhost:7860**

---

## 🔧 Troubleshooting

### ❌ Error: "name 'InsuranceClaimsOrchestrator' is not defined"

**Solution:** The UI can't find the main system file. Make sure:

1. ✅ Both files are in the **same directory**:
   ```
   my_project/
   ├── insurance_claims_ai_system.py
   └── insurance_claims_ui_FIXED.py
   ```

2. ✅ Run from the correct directory:
   ```bash
   cd my_project/
   python insurance_claims_ui_FIXED.py
   ```

3. ✅ **FIXED version** includes fallback mode - even if import fails, it works!

---

### ❌ Error: "PDF file not found"

**Solution:**

1. ✅ Place your PDF in the **same directory** as the scripts:
   ```
   my_project/
   ├── insurance_claims_ai_system.py
   ├── insurance_claims_ui_FIXED.py
   └── MERCURY AUTO INSURANCE POLICY.pdf  ← Add your PDF here
   ```

2. ✅ Or update the path in the Setup tab:
   - If PDF is in `Documents/`: `Documents/MERCURY AUTO INSURANCE POLICY.pdf`
   - If PDF is elsewhere: `/full/path/to/policy.pdf`

3. ✅ **Demo mode** activates automatically if PDF not found - you can still test!

---

### ❌ Error: "GROQ_API_KEY not set"

**Solution:**

```bash
# Check if key is set
echo $GROQ_API_KEY

# If empty, set it
export GROQ_API_KEY="gsk_your_key_here"

# Then run
python insurance_claims_ui_FIXED.py
```

**Get a free API key:** https://console.groq.com

---

### ❌ Error: "ModuleNotFoundError: No module named 'langchain'"

**Solution:**

```bash
# Reinstall all dependencies
pip install --upgrade -q langchain langchain-community langchain-groq
pip install --upgrade -q chromadb pypdf sentence-transformers
pip install --upgrade -q gradio
```

---

### ⚠️ "System not initialized" when clicking buttons

**Solution:**

1. Click the **Setup** tab first
2. Enter your PDF path (or leave default)
3. Click **🚀 Initialize System**
4. Wait for ✅ confirmation
5. Now you can use other tabs

---

## 📋 File-by-File Guide

### `insurance_claims_ai_system.py` (Main System)
- **What:** Core AI, Vector DB, Kafka, agents, Guidewire API
- **Size:** ~400 lines
- **Requires:** `insurance_claims_ai_system.py` must exist for REAL mode
- **Run:** `python insurance_claims_ai_system.py` (for testing standalone)

### `insurance_claims_ui_FIXED.py` (Web Interface) ✅
- **What:** Gradio UI with 6 tabs
- **Size:** ~450 lines
- **NEW:** Built-in fallback mode - works even if main system import fails!
- **Run:** `python insurance_claims_ui_FIXED.py`

### `MERCURY AUTO INSURANCE POLICY.pdf` (Your Policy)
- **What:** Insurance policy document to analyze
- **Action:** Place in same directory as scripts
- **Optional:** Works without it (demo mode activates)

---

## 🟢 Demo Mode vs 🔴 Real PDF Mode

### 🟡 Demo Mode (Fallback)
**When:** PDF not found OR import fails
- ✅ Works with sample data
- ✅ Test all features
- ✅ Mock Vector DB with sample answers
- ❌ Not real policy analysis

### 🟢 Real PDF Mode
**When:** Both files present AND `insurance_claims_ai_system.py` imported successfully
- ✅ Real policy analysis via RAG
- ✅ Semantic search in embeddings
- ✅ Production-ready
- ⚠️ Requires GROQ_API_KEY

**To switch to Real PDF Mode:**
1. Get API key from https://console.groq.com
2. `export GROQ_API_KEY="your_key"`
3. Place PDF in same directory
4. Restart app
5. Look for 🟢 REAL PDF MODE in Architecture tab

---

## 🎯 Next Steps After Setup

### 1. Test Policy Q&A
```
Tab: "❓ Policy Q&A"
Question: "What is the coverage limit for total loss?"
Expected: Policy answer from your PDF
```

### 2. File a Sample Claim
```
Tab: "📝 File Claim"
- Customer ID: CUST-001
- Policy ID: POL-12345
- Claim Type: total-loss
- Description: 2018 Honda Civic - totaled in accident
- Damage Assessment: Total damage - vehicle not repairable
Click: ✅ File Claim
Expected: Claim ID generated
```

### 3. Process Claims
```
Tab: "⚙️ Process Claims"
Click: ⚡ Process All Claims
Expected: Agent evaluations appear
```

### 4. Review Approval Queue
```
Tab: "✅ Approval Queue"
Click: 🔄 Refresh Queue
Expected: Human adjuster queue with recommendations
```

---

## 📊 System Architecture

```
UI (Gradio)
    ↓
initialize_system() → Creates InsuranceClaimsOrchestrator
    ↓
    ├─ Vector DB (policy embeddings)
    ├─ Kafka Topic (claim-events)
    ├─ AI Agents (Total Loss, Fraud, Billing)
    └─ Guidewire API (approval queue)
```

---

## 🔐 Security Notes

1. **Never commit API keys** to git
2. **Use environment variables** for secrets
3. **Store credentials** in `.env` file:
   ```
   # .env
   GROQ_API_KEY=gsk_your_key
   GUIDEWIRE_API_KEY=your_key
   ```
4. **Load from .env:**
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   api_key = os.getenv("GROQ_API_KEY")
   ```

---

## 📈 What Each Tab Does

| Tab | Purpose | Status |
|-----|---------|--------|
| 🔧 Setup | Initialize system with PDF | Start here |
| ❓ Policy Q&A | Ask questions about policy | Requires initialization |
| 📝 File Claim | Submit a new claim (producer) | Requires initialization |
| ⚙️ Process Claims | Run AI agents on claims (consumer) | Requires filed claims |
| ✅ Approval Queue | View recommendations for human review | Requires processed claims |
| 🏗️ Architecture | See system diagram & status | Always available |

---

## ✨ Expected Workflow

```
1. Setup Tab
   ├─ Enter: MERCURY AUTO INSURANCE POLICY.pdf
   └─ Click: Initialize System
      → ✅ System initialized

2. Policy Q&A Tab
   ├─ Ask: "What is total loss coverage?"
   └─ Get: Policy answer from PDF

3. File Claim Tab
   ├─ Enter: Customer ID, Policy ID, Description
   ├─ Click: File Claim
   └─ Get: Claim ID (e.g., CLM-20240412120000-CUS)

4. Process Claims Tab
   ├─ Click: Process All Claims
   └─ Get: Agent evaluations
      ├─ Total Loss Agent → APPROVE (95%)
      ├─ Fraud Agent → PROCEED (98%)
      └─ Billing Agent → APPROVE (99%)

5. Approval Queue Tab
   ├─ Click: Refresh Queue
   └─ Get: Claims ready for human adjuster
      ├─ Claim ID: CLM-20240412120000-CUS
      ├─ Recommendation: APPROVE
      ├─ Payout: $24,500
      └─ Confidence: 95%

6. Human Adjuster
   ├─ Reviews recommendations
   ├─ Approves/Denies claim
   └─ Initiates payment
```

---

## 🐛 Debug Mode

To see detailed logs:

```python
# In insurance_claims_ui_FIXED.py, change:
logging.basicConfig(level=logging.DEBUG)  # Instead of INFO

# Or from terminal:
export LOG_LEVEL=DEBUG
python insurance_claims_ui_FIXED.py
```

---

## 🚀 Production Deployment

To deploy to production:

1. **Install gunicorn:**
   ```bash
   pip install gunicorn
   ```

2. **Create app wrapper:**
   ```python
   # app.py
   from insurance_claims_ui_FIXED import create_ui
   app = create_ui()
   ```

3. **Run with gunicorn:**
   ```bash
   gunicorn --workers 4 --timeout 120 app:app
   ```

4. **Or use Docker:**
   ```dockerfile
   FROM python:3.10
   COPY . /app
   WORKDIR /app
   RUN pip install -r requirements.txt
   CMD ["python", "insurance_claims_ui_FIXED.py"]
   ```

---

## 📞 Quick Reference

**Start from scratch:**
```bash
pip install -q langchain langchain-community langchain-groq chromadb pypdf sentence-transformers gradio
export GROQ_API_KEY="your_key"
python insurance_claims_ui_FIXED.py
```

**File structure:**
```
project/
├── insurance_claims_ai_system.py    (Main system)
├── insurance_claims_ui_FIXED.py     (Web UI)
├── MERCURY AUTO INSURANCE POLICY.pdf (Optional - for real mode)
└── .env                             (Optional - for API keys)
```

**Common issues:**
- ✅ Import errors? → Use FIXED version (has fallback)
- ✅ PDF not found? → Demo mode activates automatically
- ✅ API key error? → Set `GROQ_API_KEY` environment variable
- ✅ Can't initialize? → Check both files in same directory

---

**Ready to test? Open http://localhost:7860 after running the script!** 🎉
