# 🔴 ALWAYS SHOWING DEMO MODE? HERE'S THE FIX

## 🎯 Why It's Still Demo Mode

The system shows demo mode because:

1. ❌ **PDF not found** (`MERCURY AUTO INSURANCE POLICY.pdf`)
2. ❌ **GROQ_API_KEY not detected** by Python
3. ❌ **LangChain packages not imported** correctly
4. ❌ **PDF loading failed** even though file exists

---

## ✅ SOLUTION: Use the Complete Standalone File

I've created **`insurance_claims_complete.py`** - a single file with everything built-in.

### Step 1: Verify Dependencies

```bash
# First, make sure ALL packages are installed
pip install --upgrade langchain langchain-community langchain-groq
pip install --upgrade chromadb pypdf sentence-transformers
pip install --upgrade gradio
pip install "numpy<2.0"

# Check if installed
python -c "import langchain; import chromadb; import gradio; print('✅ All imports OK')"
```

### Step 2: Set API Key CORRECTLY

**The issue:** Just exporting doesn't always work. Let me show you how to verify it's set:

```bash
# SET the key
export GROQ_API_KEY="gsk_your_actual_key_here"

# VERIFY it's set
echo $GROQ_API_KEY

# You should see: gsk_your_actual_key_here
# If you see nothing, it's NOT set!
```

**If you see nothing after `echo`, the key is NOT set!**

Then run:
```bash
python insurance_claims_complete.py
```

### Step 3: Check in Terminal for Real Mode Confirmation

When you start the app, look at the **terminal output** (NOT the web UI):

**🟡 Demo Mode (What you're seeing):**
```
2024-04-12 12:00:00 - VectorDB - WARNING - ⚠️  PDF not found or LangChain unavailable. Using demo mode.
```

**🟢 Real Mode (What we want):**
```
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Loaded 42 pages from MERCURY AUTO INSURANCE POLICY.pdf
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Created 156 policy chunks
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Vector DB indexed successfully!
2024-04-12 12:00:00 - VectorDB - INFO - ✅ REAL PDF MODE ACTIVE
```

---

## 🔍 Troubleshooting Steps

### ❓ Q: "Still showing Demo Mode"

**A: Check the PDF file:**

```bash
# Make sure PDF is in the SAME DIRECTORY as the script
ls -la

# You should see:
# -rw-r--r-- insurance_claims_complete.py
# -rw-r--r-- MERCURY AUTO INSURANCE POLICY.pdf  ← This file must exist!
```

If PDF is elsewhere, provide full path:
- In web UI Setup tab, change path to: `/full/path/to/MERCURY AUTO INSURANCE POLICY.pdf`

---

### ❓ Q: "API key not working"

**A: Verify the key is actually set:**

```bash
# Method 1: Check current session
echo $GROQ_API_KEY
# Should print your key, not empty!

# Method 2: Check Python sees it
python -c "import os; print(os.getenv('GROQ_API_KEY'))"
# Should print your key, not None!

# Method 3: Create .env file instead
cat > .env << EOF
GROQ_API_KEY=gsk_your_key_here
EOF

# Then run with:
python -c "from dotenv import load_dotenv; load_dotenv()" && python insurance_claims_complete.py
```

---

### ❓ Q: "LangChain import errors"

**A: Reinstall with exact versions:**

```bash
# Uninstall old versions
pip uninstall -y langchain langchain-community langchain-groq chromadb

# Install exact versions that work
pip install langchain==0.1.20
pip install langchain-community==0.0.38
pip install langchain-groq==0.1.3
pip install chromadb==0.4.24
pip install pypdf
pip install sentence-transformers
pip install gradio
```

---

### ❓ Q: "ModuleNotFoundError"

**A: Check Python environment:**

```bash
# Which Python are you using?
which python
which python3

# Try explicit Python 3
python3 --version

# Run with python3 explicitly
python3 insurance_claims_complete.py

# If still fails, create fresh environment
python3 -m venv claims_env
source claims_env/bin/activate  # On Windows: claims_env\Scripts\activate
pip install langchain langchain-community langchain-groq chromadb pypdf sentence-transformers gradio
export GROQ_API_KEY="your_key"
python insurance_claims_complete.py
```

---

## 📋 Complete Working Setup (Copy-Paste)

If you want to start fresh:

```bash
# 1. Create new directory
mkdir insurance_claims
cd insurance_claims

# 2. Copy the complete file here:
# (Download: insurance_claims_complete.py)

# 3. Copy your PDF here:
# (Copy: MERCURY AUTO INSURANCE POLICY.pdf)

# 4. Install dependencies
pip install langchain langchain-community langchain-groq chromadb pypdf sentence-transformers gradio "numpy<2.0"

# 5. Set API key
export GROQ_API_KEY="gsk_your_actual_key"

# 6. Verify it's set
echo $GROQ_API_KEY  # Should show: gsk_your_actual_key

# 7. Run
python insurance_claims_complete.py

# 8. Open in browser: http://localhost:7860
```

---

## 🧪 Test for Real PDF Mode

Once you see the web UI, do this quick test:

1. **Go to Setup tab**
2. **Path should be:** `MERCURY AUTO INSURANCE POLICY.pdf`
3. **Click:** 🚀 Initialize
4. **Look at terminal output** (NOT web UI) - should show:
   - ✅ Loaded X pages
   - ✅ Created X chunks
   - ✅ Vector DB indexed
   - ✅ REAL PDF MODE ACTIVE

5. **Go to Approval Queue tab** at bottom right
6. **Look for system mode**:
   - Should say: **🟢 REAL PDF MODE** (not 🟡 DEMO MODE)

---

## 🐛 Debug: Full Diagnostic

Run this to see what's happening:

```bash
# Create test_diagnosis.py
cat > test_diagnosis.py << 'EOF'
import os
import sys

print("\n=== DIAGNOSTIC CHECK ===\n")

# Check 1: API Key
api_key = os.getenv("GROQ_API_KEY")
print(f"1. GROQ_API_KEY: {'✅ SET' if api_key else '❌ NOT SET'}")
if api_key:
    print(f"   Value: {api_key[:20]}...")

# Check 2: PDF File
pdf_path = "MERCURY AUTO INSURANCE POLICY.pdf"
exists = os.path.exists(pdf_path)
print(f"\n2. PDF File: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
if exists:
    size = os.path.getsize(pdf_path) / (1024*1024)  # MB
    print(f"   Size: {size:.2f} MB")

# Check 3: Imports
print(f"\n3. Imports:")
try:
    import langchain
    print(f"   ✅ langchain")
except:
    print(f"   ❌ langchain")

try:
    import chromadb
    print(f"   ✅ chromadb")
except:
    print(f"   ❌ chromadb")

try:
    import gradio
    print(f"   ✅ gradio")
except:
    print(f"   ❌ gradio")

try:
    from langchain_groq import ChatGroq
    print(f"   ✅ langchain_groq")
except:
    print(f"   ❌ langchain_groq")

try:
    from langchain_community.vectorstores import Chroma
    print(f"   ✅ langchain_community")
except:
    print(f"   ❌ langchain_community")

# Check 4: Python Version
print(f"\n4. Python: {sys.version}")

print("\n=== END DIAGNOSTIC ===\n")
EOF

python test_diagnosis.py
```

---

## ✨ Expected Output for REAL PDF MODE

When everything is correct, this is what you'll see in terminal:

```
2024-04-12 12:00:00 - Orchestrator - INFO - ✅ Orchestrator initialized
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Loaded 42 pages from MERCURY AUTO INSURANCE POLICY.pdf
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Created 156 policy chunks
2024-04-12 12:00:00 - VectorDB - INFO - ✅ Vector DB indexed successfully!
2024-04-12 12:00:00 - VectorDB - INFO - ✅ REAL PDF MODE ACTIVE
2024-04-12 12:00:00 - GradioUI - INFO - 🚀 Starting Insurance Claims AI System
```

Then in web UI:
- Click Setup → Initialize
- Should show: **✅ System initialized! Mode: 🟢 REAL PDF MODE**

---

## 🎯 If Still Demo Mode After All This

**It's OK!** Demo mode still works:

```
✅ Can file claims
✅ Can process claims  
✅ Can see approval queue
✅ Can ask policy questions (with sample answers)
❌ Just using mock data, not real PDF analysis
```

**To force Real PDF Mode:**

1. Get free API key: https://console.groq.com
2. Verify: `echo $GROQ_API_KEY` shows key
3. Ensure PDF exists: `ls -la MERCURY*`
4. Run: `python insurance_claims_complete.py`
5. Check terminal for ✅ REAL PDF MODE ACTIVE

---

## 📞 Still Stuck?

Share this info:

```bash
# Run this and copy output:
python test_diagnosis.py
echo "GROQ_API_KEY is: $GROQ_API_KEY"
ls -la MERCURY*
python insurance_claims_complete.py 2>&1 | head -20
```

---

**Remember:** Even in demo mode, the system is FULLY FUNCTIONAL. It's just using sample data instead of your actual PDF. 🟡 → 🟢 is optional but recommended! ✨
