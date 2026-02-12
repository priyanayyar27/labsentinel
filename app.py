"""
LabSentinel - AI-Powered Lab Data Integrity Auditor
Uses NVIDIA Nemotron models to cross-reference lab imagery against SOPs
and flag data integrity discrepancies in pharmaceutical R&D.
"""

import streamlit as st
import base64
import os
import json
import re
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from sample_sops import SAMPLE_SOPS

# ============================================================
# SETUP: Load API key and configure NVIDIA API client
# ============================================================

# Load the .env file (which contains your NVIDIA_API_KEY)
load_dotenv()

# Get the API key from the .env file
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# Create the API client that talks to NVIDIA's servers
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# ============================================================
# PERSISTENT CACHE: Save AI results to disk so they survive restarts
# ============================================================
# This ensures the same image + SOP always produces the same score,
# even if the app is restarted. Critical for data integrity tool credibility.

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".labsentinel_cache.json")

def load_cache():
    """Load the persistent cache from disk."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {}

def save_cache(cache):
    """Save the cache to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except IOError:
        pass

def get_cached(key):
    """Get a value from the persistent cache."""
    cache = load_cache()
    return cache.get(key, None)

def set_cached(key, value):
    """Set a value in the persistent cache."""
    cache = load_cache()
    cache[key] = value
    save_cache(cache)

# ============================================================
# HELPER FUNCTION: Convert an uploaded image to base64
# ============================================================
# Why? The API can't receive image files directly. We need to convert
# the image into a text string (base64) that can be sent over the internet.

def image_to_base64(uploaded_file):
    """Convert an uploaded image file to a base64 string."""
    bytes_data = uploaded_file.getvalue()
    base64_string = base64.b64encode(bytes_data).decode("utf-8")
    return base64_string


# ============================================================
# CORE FUNCTION 1: Analyze the lab image using Nemotron Vision
# ============================================================
# This sends the lab image to NVIDIA's vision model and asks it
# to describe what it sees in scientific detail.

def analyze_lab_image(image_base64, image_type="image/jpeg"):
    """
    Send a lab image to Nemotron Nano VL (Vision-Language) model for detailed analysis.
    Returns a text description of what the AI observes in the image.
    """
    # Try the Nemotron VL model first, then fall back to other available vision models
    vision_models = [
        "nvidia/nemotron-nano-12b-v2-vl",
        "nvidia/vlm-1b-instruct",
        "google/gemma-3-27b-it",
        "meta/llama-3.2-11b-vision-instruct",
    ]
    
    prompt_text = """You are an expert pharmaceutical laboratory analyst with 20 years 
of experience in quality control and GMP compliance. Analyze this laboratory image in precise scientific detail.

FIRST, identify the experiment type. State ONE of these on the very first line:
EXPERIMENT_TYPE: MTT_CELL_VIABILITY (if you see a multi-well plate with purple/blue colored wells)
EXPERIMENT_TYPE: GEL_ELECTROPHORESIS (if you see a gel with bands/lanes under UV or visible light)
EXPERIMENT_TYPE: HPLC_CHROMATOGRAPHY (if you see a chromatogram chart with peaks)
EXPERIMENT_TYPE: COLONY_COUNTING (if you see petri dishes with bacterial colonies)
EXPERIMENT_TYPE: OTHER (if none of the above)

THEN describe EXACTLY what you observe:
1. Overall image quality and clarity
2. Sample conditions (color, turbidity, uniformity, morphology)
3. Any visible anomalies, contamination, or irregularities
4. Equipment/setup observations (if visible)
5. Any signs of procedural deviation

Be extremely specific and quantitative where possible. Flag anything 
that looks unusual, inconsistent, or potentially problematic. 
Your observations will be compared against the Standard Operating Procedure."""

    last_error = None
    for model_name in vision_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            continue
    
    # If all vision models fail, return error
    return f"Vision analysis error: {last_error}. All vision models unavailable. Please check your API key and try again."


# ============================================================
# CORE FUNCTION 2: Compare image analysis against SOP
# ============================================================
# This is the "brain" of LabSentinel. It takes what the vision model
# saw in the image AND the SOP protocol, then reasons about whether
# they match or conflict.

def compare_with_sop(image_analysis, sop_text):
    """
    Use Nemotron reasoning model to compare image observations against SOP.
    Returns a structured audit report with integrity score and flags.
    """
    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-nano-30b-a3b",
            messages=[
                {
                    "role": "system",
                    "content": """You are LabSentinel, an AI-powered pharmaceutical data integrity auditor. 
Your role is to compare laboratory visual evidence against Standard Operating Procedures (SOPs) 
to detect data integrity issues, procedural deviations, and potential reproducibility failures.

You must be thorough, precise, and unbiased. You flag issues that human reviewers might miss 
due to confirmation bias or time pressure. Your analysis helps prevent the $28 billion/year 
reproducibility crisis in preclinical research.

IMPORTANT: Always respond with the structured JSON format requested. Be specific about 
which SOP criteria each finding relates to."""
                },
                {
                    "role": "user",
                    "content": f"""Perform a complete data integrity audit by comparing the laboratory image analysis 
against the Standard Operating Procedure.

## LABORATORY IMAGE ANALYSIS (from vision model):
{image_analysis}

## STANDARD OPERATING PROCEDURE:
{sop_text}

## YOUR TASK:
Generate a comprehensive audit report in the following JSON format:

{{
    "data_integrity_score": <integer 0-100, where 100 = perfect compliance>,
    "overall_status": "<PASS | INVESTIGATE | FAIL>",
    "summary": "<2-3 sentence executive summary>",
    "findings": [
        {{
            "id": "F001",
            "severity": "<CRITICAL | MAJOR | MINOR | OBSERVATION>",
            "category": "<Contamination | Procedural Deviation | Data Discrepancy | Equipment Issue | Documentation Gap>",
            "observation": "<what was observed in the image>",
            "sop_requirement": "<what the SOP specifies>",
            "discrepancy": "<specific mismatch between observation and SOP>",
            "impact": "<potential impact on data integrity and reproducibility>",
            "recommendation": "<specific corrective action>"
        }}
    ],
    "sop_compliance_checklist": [
        {{
            "criterion": "<SOP requirement>",
            "status": "<COMPLIANT | NON-COMPLIANT | UNABLE TO ASSESS>",
            "notes": "<brief explanation>"
        }}
    ],
    "risk_assessment": "<brief paragraph on overall risk to data integrity>",
    "recommended_actions": ["<action 1>", "<action 2>", "<action 3>"]
}}

Be thorough but fair. Only flag genuine concerns, not speculative issues.
If the image quality prevents assessment of certain criteria, mark them as UNABLE TO ASSESS.
Respond ONLY with the JSON object, no additional text before or after it."""
                }
            ],
            max_tokens=4000,
            temperature=0.0,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False}
            }
        )
        return response.choices[0].message.content

    except Exception as e:
        return json.dumps({
            "data_integrity_score": 0,
            "overall_status": "ERROR",
            "summary": f"Audit could not be completed: {str(e)}",
            "findings": [],
            "sop_compliance_checklist": [],
            "risk_assessment": "Unable to assess due to API error.",
            "recommended_actions": ["Check API key", "Verify model availability", "Try again"]
        })


# ============================================================
# HELPER FUNCTION: Parse the JSON response from the AI
# ============================================================

def parse_audit_response(response_text):
    """Try to parse the AI's response as JSON. Handle common formatting issues."""
    result = None
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group(0))
        except (json.JSONDecodeError, AttributeError):
            pass
    
    if result is None:
        return {
            "data_integrity_score": None,
            "overall_status": "PARSE_ERROR",
            "summary": "The AI generated a response but it could not be parsed as structured data. Raw response is shown below.",
            "raw_response": response_text,
            "findings": [],
            "sop_compliance_checklist": [],
            "risk_assessment": response_text,
            "recommended_actions": ["Review raw AI output manually"]
        }
    
    # ---- DETERMINISTIC SCORING ----
    # Calculate score from checklist and findings instead of trusting the AI's number.
    # This ensures the same checklist = the same score every time.
    
    checklist = result.get("sop_compliance_checklist", [])
    findings = result.get("findings", [])
    
    if checklist:
        compliant = sum(1 for item in checklist if item.get("status", "").upper() == "COMPLIANT")
        non_compliant = sum(1 for item in checklist if item.get("status", "").upper() == "NON-COMPLIANT")
        unable = sum(1 for item in checklist if item.get("status", "").upper() == "UNABLE TO ASSESS")
        total = compliant + non_compliant + unable
        
        if total > 0:
            # Compliant items get full marks, unable-to-assess get half marks (benefit of doubt)
            raw_score = ((compliant * 1.0) + (unable * 0.5)) / total * 100
            
            # Deduct points for findings by severity
            severity_penalties = {"CRITICAL": 15, "MAJOR": 10, "MINOR": 5, "OBSERVATION": 2}
            penalty = sum(severity_penalties.get(f.get("severity", "").upper(), 0) for f in findings)
            
            calculated_score = max(0, min(100, round(raw_score - penalty)))
        else:
            calculated_score = result.get("data_integrity_score", 50)
    else:
        calculated_score = result.get("data_integrity_score", 50)
    
    # Override the AI's subjective score with our calculated one
    result["data_integrity_score"] = calculated_score
    
    # Determine status from calculated score (fixed thresholds)
    if calculated_score >= 80:
        result["overall_status"] = "PASS"
    elif calculated_score >= 50:
        result["overall_status"] = "INVESTIGATE"
    else:
        result["overall_status"] = "FAIL"
    
    return result


# ============================================================
# STREAMLIT UI: Build the web interface
# ============================================================

# Page configuration
st.set_page_config(
    page_title="LabSentinel | AI Data Integrity Auditor",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global */
    .stApp { background-color: #0b0b10; }
    header[data-testid="stHeader"] { background-color: #0b0b10 !important; }
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp div {
        font-family: 'DM Sans', sans-serif !important;
        color: #d0d0dc;
        font-size: 1.05rem;
    }
    
    /* Section titles */
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Score boxes (fallback for st.markdown) */
    .score-box { padding: 2rem; border-radius: 16px; text-align: center; margin: 1rem 0; }
    
    /* Finding cards */
    .finding-card {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .finding-critical { border-left: 4px solid #ff4d5e; }
    .finding-major { border-left: 4px solid #ffb020; }
    .finding-minor { border-left: 4px solid #20b2ff; }
    .finding-observation { border-left: 4px solid #555; }
    .finding-card strong { color: #ffffff; }
    .finding-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #606070;
        margin-top: 0.5rem;
        display: block;
    }
    .finding-value {
        font-size: 0.88rem;
        color: #b0b0c0;
        line-height: 1.5;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0d0d14;
        border-right: 1px solid rgba(118, 185, 0, 0.1);
    }
    .stat-row {
        display: flex;
        gap: 10px;
        margin-bottom: 8px;
        align-items: baseline;
    }
    .stat-number {
        font-family: 'JetBrains Mono', monospace !important;
        color: #76b900;
        font-weight: 700;
        font-size: 0.95rem;
        min-width: 48px;
    }
    .stat-text {
        color: #8a8a96;
        font-size: 0.92rem;
    }
    
    /* Form elements - dark */
    .stFileUploader > div > div {
        border: 1px dashed rgba(118, 185, 0, 0.25) !important;
        border-radius: 12px !important;
        background: #14141e !important;
    }
    .stFileUploader > div { background: transparent !important; }
    .stFileUploader button {
        background-color: rgba(118, 185, 0, 0.15) !important;
        color: #76b900 !important;
        border: 1px solid rgba(118, 185, 0, 0.3) !important;
        border-radius: 8px !important;
    }
    .stFileUploader p, .stFileUploader span { color: #707080 !important; }
    div[data-testid="stFileUploader"] > div:first-child { background-color: #14141e !important; }
    [data-baseweb="select"] > div {
        background-color: #14141e !important;
        border-color: rgba(118, 185, 0, 0.2) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"] { background-color: #14141e !important; }
    [role="option"] { background-color: #14141e !important; color: #d0d0dc !important; }
    [role="option"]:hover { background-color: rgba(118, 185, 0, 0.1) !important; }
    .stAlert {
        background-color: rgba(118, 185, 0, 0.06) !important;
        border: 1px solid rgba(118, 185, 0, 0.15) !important;
        border-radius: 10px !important;
    }
    .uploadedFile {
        background-color: #14141e !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 8px !important;
    }
    
    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #76b900, #5a8f00) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(118, 185, 0, 0.25) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(118, 185, 0, 0.1) !important;
        border: 1px solid rgba(118, 185, 0, 0.3) !important;
        color: #76b900 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(118, 185, 0, 0.2) !important;
    }
    
    /* Expander fix */
    .stExpander { margin-top: 0.5rem !important; margin-bottom: 1rem !important; }
    details[data-testid="stExpander"] summary {
        background: #14141e !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 8px !important;
    }
    details[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        background: #101018 !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
        border-top: none !important;
    }
    
    /* iframe height fix for st.html */
    iframe[data-testid="stAppIframeResizer"] { min-height: 0 !important; }
    div[data-testid="stAppIframeResizerAnchor"] { min-height: 0 !important; }
    
    /* Code block styling (View Protocol) */
    .stCode, div[data-testid="stCode"] {
        background-color: #12121a !important;
        border: 1px solid rgba(118, 185, 0, 0.25) !important;
        border-radius: 10px !important;
    }
    .stCode pre, div[data-testid="stCode"] pre {
        background-color: #12121a !important;
        color: #d0d0dc !important;
    }
    .stCode code, div[data-testid="stCode"] code {
        background-color: transparent !important;
        color: #d0d0dc !important;
    }
    
    /* Divider */
    hr { border-color: rgba(255, 255, 255, 0.04) !important; }
    .stImage > div > div > p { color: #505060 !important; }
</style>
""", unsafe_allow_html=True)

# ---- HERO HEADER (compact + punchy) ----
st.html("""
<div style="background:linear-gradient(135deg, #10101a 0%, #161625 40%, #0f1a0f 100%); border:1px solid rgba(118,185,0,0.15); border-radius:20px; padding:2.5rem 3rem 2rem; margin-bottom:1.5rem; position:relative; overflow:hidden; font-family:'DM Sans',sans-serif;">
    <div style="display:flex; align-items:center; gap:1.5rem; margin-bottom:12px;">
        <div style="font-size:72px; font-weight:800; color:#ffffff; letter-spacing:-2px; line-height:1;">Lab<span style="color:#76b900; font-size:72px; font-weight:800;">Sentinel</span></div>
    </div>
    <div style="font-size:22px; color:#b0b0c0; font-weight:500; margin-bottom:16px;">Catches data integrity issues that human auditors miss.</div>
    <div style="display:flex; gap:2rem; flex-wrap:wrap; align-items:center;">
        <span style="font-size:13px; color:#606070; font-family:'JetBrains Mono',monospace;">⚡ <span style="color:#76b900;">Nemotron Nano VL</span> — Vision</span>
        <span style="font-size:13px; color:#606070; font-family:'JetBrains Mono',monospace;">🧠 <span style="color:#76b900;">Nemotron 3 Nano</span> — Reasoning</span>
        <span style="font-size:13px; color:#606070; font-family:'JetBrains Mono',monospace;">☁️ <span style="color:#76b900;">NVIDIA NIM API</span></span>
    </div>
</div>
""")

# Check if API key is configured
if not NVIDIA_API_KEY:
    st.error("⚠️ NVIDIA API Key not found! Please add your key to the `.env` file. See README for setup instructions.")
    st.stop()

# ---- SIDEBAR ----
with st.sidebar:
    # Social proof / differentiator at the TOP
    st.html("""
    <div style="background:rgba(118,185,0,0.06); border:1px solid rgba(118,185,0,0.2); border-radius:12px; padding:1rem 1.2rem; margin-bottom:1rem; font-family:'DM Sans',sans-serif;">
        <div style="font-size:14px; font-weight:700; color:#76b900; margin-bottom:6px;">🏆 NVIDIA GTC 2026 Golden Ticket</div>
        <div style="font-size:13px; color:#9090a0; line-height:1.5;">Built by a product & marketing leader with experience at <span style="color:#d0d0dc; font-weight:600;">GSK, Agoda & Rocket Internet</span> — who saw pharma's data integrity crisis up close.</div>
    </div>
    """)
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">🧪 Why This Matters</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-number">$28B</span><span class="stat-text">wasted yearly on irreproducible research</span></div>
    <div class="stat-row"><span class="stat-number">50%+</span><span class="stat-text">preclinical studies can't be replicated</span></div>
    <div class="stat-row"><span class="stat-number">+50%</span><span class="stat-text">jump in FDA warning letters (2025)</span></div>
    <div class="stat-row"><span class="stat-number">#1</span><span class="stat-text">compliance issue: data integrity</span></div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">📋 How It Works</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-number">1.</span><span class="stat-text">Upload a lab image from your experiment</span></div>
    <div class="stat-row"><span class="stat-number">2.</span><span class="stat-text">Select the matching SOP protocol</span></div>
    <div class="stat-row"><span class="stat-number">3.</span><span class="stat-text">Click audit — AI flags discrepancies in seconds</span></div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">🚀 Roadmap</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-text">🔄 Multi-image batch auditing</span></div>
    <div class="stat-row"><span class="stat-text">📊 Raw instrument data analysis</span></div>
    <div class="stat-row"><span class="stat-text">🏥 LIMS & e-lab notebook integration</span></div>
    <div class="stat-row"><span class="stat-text">📋 Auto-generated regulatory reports</span></div>
    <div class="stat-row"><span class="stat-text">⚡ <span style="color:#76b900; font-weight:600;">Nemotron Ultra on NVIDIA DGX</span> for production deployment</span></div>
    """, unsafe_allow_html=True)

# ---- MAIN CONTENT: Vertical flow (1 → 2 → 3) ----

# STEP 1: Upload
st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.5rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:4px;">Step 1</div>')
st.markdown('<div class="section-title">📤 Upload Lab Image</div>', unsafe_allow_html=True)

col_upload, col_preview = st.columns([1, 1])
with col_upload:
    uploaded_image = st.file_uploader(
        "Upload a lab image",
        type=["jpg", "jpeg", "png", "bmp", "tiff"],
        help="Supported formats: JPG, PNG, BMP, TIFF. Max size: 20MB",
        label_visibility="collapsed"
    )
with col_preview:
    if uploaded_image is not None:
        st.image(uploaded_image, caption="Uploaded Lab Image", use_container_width=True)

st.markdown("---")

# STEP 2: Select SOP
st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.5rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:4px;">Step 2</div>')
st.markdown('<div class="section-title">📄 Select Protocol (SOP)</div>', unsafe_allow_html=True)

col_sop, col_sop_detail = st.columns([1, 1])
with col_sop:
    sop_choice = st.radio(
        "Choose an SOP to audit against:",
        options=["Select a sample SOP", "Paste custom SOP"],
        help="Sample SOPs are provided for demo purposes. In production, these would come from your lab's QMS.",
        label_visibility="collapsed"
    )
    
    if sop_choice == "Select a sample SOP":
        selected_sop = st.selectbox(
            "Sample SOPs:",
            options=list(SAMPLE_SOPS.keys()),
            label_visibility="collapsed"
        )
        sop_text = SAMPLE_SOPS[selected_sop]
        
        # View Protocol toggle
        if "show_sop" not in st.session_state:
            st.session_state.show_sop = False
        view_btn = st.button(f"👁️ View Protocol: {selected_sop}", key="view_sop_btn")
        if view_btn:
            st.session_state.show_sop = not st.session_state.show_sop
    else:
        sop_text = st.text_area(
            "Paste your SOP text here:",
            height=200,
            placeholder="Paste the Standard Operating Procedure text for this experiment..."
        )

with col_sop_detail:
    if sop_choice == "Select a sample SOP" and st.session_state.get("show_sop", False):
        st.code(sop_text, language=None)
    elif sop_choice == "Select a sample SOP":
        pass  # Protocol preview appears here when button is clicked

st.markdown("---")

# STEP 3: Run Audit + Results
st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.5rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:4px;">Step 3</div>')
st.markdown('<div class="section-title">📊 Run Audit & View Results</div>', unsafe_allow_html=True)

audit_button = st.button(
    "🔍 Run Data Integrity Audit",
    type="primary",
    use_container_width=True,
    disabled=(uploaded_image is None or not sop_text)
)

if uploaded_image is None:
    pass  # Instructions already in sidebar

# ---- RUN THE AUDIT ----
if audit_button and uploaded_image is not None and sop_text:
    
    # Determine image type
    image_type = f"image/{uploaded_image.type.split('/')[-1]}" if uploaded_image.type else "image/jpeg"
    
    # Convert image to base64
    image_b64 = image_to_base64(uploaded_image)
    
    # Create a unique hash for this image to use as cache key
    image_hash = hashlib.md5(image_b64.encode()[:1000]).hexdigest()
    
    # STEP 1: Analyze the image (CACHED TO DISK - same image = same analysis forever)
    cache_key = f"vision_{image_hash}"
    cached_vision = get_cached(cache_key)
    if cached_vision:
        image_analysis = cached_vision
        with st.spinner("🔬 Step 1/2: Using cached image analysis..."):
            pass
    else:
        with st.spinner("🔬 Step 1/2: Analyzing lab image with Nemotron Vision..."):
            image_analysis = analyze_lab_image(image_b64, image_type)
            set_cached(cache_key, image_analysis)
    
    # STEP 1.5: Check if image matches the selected SOP
    # Uses THREE signals: vision model classification, filename, and description keywords
    is_mismatch = False
    
    # Map SOP keywords to expected experiment types
    sop_to_experiment = {
        "mtt": "MTT_CELL_VIABILITY",
        "cell viability": "MTT_CELL_VIABILITY",
        "sop-cv": "MTT_CELL_VIABILITY",
        "gel": "GEL_ELECTROPHORESIS",
        "electrophoresis": "GEL_ELECTROPHORESIS",
        "sop-ge": "GEL_ELECTROPHORESIS",
        "hplc": "HPLC_CHROMATOGRAPHY",
        "chromatograph": "HPLC_CHROMATOGRAPHY",
        "sop-hp": "HPLC_CHROMATOGRAPHY",
        "colony": "COLONY_COUNTING",
        "cfu": "COLONY_COUNTING",
        "bacterial": "COLONY_COUNTING",
        "sop-bc": "COLONY_COUNTING",
    }
    
    # Keywords that strongly indicate each experiment type
    type_keywords = {
        "MTT_CELL_VIABILITY": ["mtt", "96-well", "microplate", "well plate", "formazan", "purple well", "cell viability"],
        "GEL_ELECTROPHORESIS": ["gel electrophoresis", "agarose", "gel band", "dna gel", "gel lane", "electrophoresis"],
        "HPLC_CHROMATOGRAPHY": ["hplc", "chromatogram", "chromatography", "retention time", "peak area"],
        "COLONY_COUNTING": ["colony count", "cfu", "petri dish", "bacterial colony", "agar plate"],
    }
    
    # SIGNAL 1: What experiment type did the vision model explicitly classify?
    detected_type = "OTHER"
    for line in image_analysis.split('\n')[:3]:
        if "EXPERIMENT_TYPE:" in line.upper():
            detected_type = line.split(":")[-1].strip().upper()
            break
    
    # SIGNAL 2: Check the filename for clues
    filename = uploaded_image.name.lower() if uploaded_image.name else ""
    filename_type = "OTHER"
    for exp_type, keywords in type_keywords.items():
        if any(kw in filename.replace("-", " ").replace("_", " ") for kw in keywords):
            filename_type = exp_type
            break
    
    # SIGNAL 3: Check the vision description text for strong keywords
    description_lower = image_analysis.lower()
    description_type = "OTHER"
    for exp_type, keywords in type_keywords.items():
        if any(kw in description_lower for kw in keywords):
            description_type = exp_type
            break
    
    # Combine signals: use the best available classification
    # Priority: explicit vision classification > filename > description keywords
    best_detected_type = detected_type
    if best_detected_type == "OTHER":
        best_detected_type = filename_type
    if best_detected_type == "OTHER":
        best_detected_type = description_type
    
    # What experiment type does the selected SOP expect?
    sop_first_line = sop_text.strip().split('\n')[0].lower()
    expected_type = None
    for keyword, exp_type in sop_to_experiment.items():
        if keyword in sop_first_line:
            expected_type = exp_type
            break
    
    # Flag mismatch if we detected a specific type AND it doesn't match the SOP
    if expected_type and best_detected_type != "OTHER" and expected_type not in best_detected_type:
        is_mismatch = True
    
    if is_mismatch:
        st.html("""
        <div style="padding:2rem; border-radius:16px; text-align:center; margin:1rem 0; background:linear-gradient(135deg, rgba(220,53,69,0.12), rgba(220,53,69,0.03)); border:1px solid rgba(220,53,69,0.4);">
            <div style="font-family:'JetBrains Mono',monospace; font-size:72px; font-weight:700; color:#ff6b7a; margin:0;">🚫 SOP MISMATCH</div>
            <div style="font-weight:600; font-size:1.2rem; text-transform:uppercase; letter-spacing:3px; color:#ff6b7a; margin-top:0.3rem;">Image does not match selected SOP</div>
        </div>
        """)
        st.error("**The uploaded image does not appear to match the selected Standard Operating Procedure.** "
                 "For example, you may have uploaded a gel electrophoresis image but selected the MTT Cell Viability SOP. "
                 "Please select the correct SOP for this image type and try again.")
        st.stop()
    
    # STEP 2: Compare with SOP (CACHED TO DISK - same image + same SOP = same result forever)
    sop_hash = hashlib.md5(sop_text.encode()).hexdigest()
    audit_cache_key = f"audit_{image_hash}_{sop_hash}"
    cached_audit = get_cached(audit_cache_key)
    if cached_audit:
        audit_response = cached_audit
        with st.spinner("🧠 Step 2/2: Using cached audit result..."):
            pass
    else:
        with st.spinner("🧠 Step 2/2: Comparing observations against SOP with Nemotron Reasoning..."):
            audit_response = compare_with_sop(image_analysis, sop_text)
            set_cached(audit_cache_key, audit_response)
    
    # Parse the response
    audit_result = parse_audit_response(audit_response)
    
    # ---- DISPLAY RESULTS ----
    
    # Score display
    score = audit_result.get("data_integrity_score", "N/A")
    status = audit_result.get("overall_status", "UNKNOWN")
    
    # Color coding based on status
    if status == "PASS":
        score_emoji = "✅"
    elif status == "INVESTIGATE":
        score_emoji = "⚠️"
    elif status == "FAIL":
        score_emoji = "❌"
    else:
        score_emoji = "❓"
    
    # Score box colors
    if status == "PASS":
        bg_color = "rgba(40,167,69,0.12)"
        bg_color2 = "rgba(40,167,69,0.03)"
        border_color = "rgba(40,167,69,0.4)"
        text_color = "#4cdf78"
    elif status == "INVESTIGATE":
        bg_color = "rgba(255,193,7,0.12)"
        bg_color2 = "rgba(255,193,7,0.03)"
        border_color = "rgba(255,193,7,0.4)"
        text_color = "#ffd44a"
    elif status == "FAIL":
        bg_color = "rgba(220,53,69,0.12)"
        bg_color2 = "rgba(220,53,69,0.03)"
        border_color = "rgba(220,53,69,0.4)"
        text_color = "#ff6b7a"
    else:
        bg_color = "rgba(255,193,7,0.12)"
        bg_color2 = "rgba(255,193,7,0.03)"
        border_color = "rgba(255,193,7,0.4)"
        text_color = "#ffd44a"
    
    st.html(f"""
    <div style="padding:2rem; border-radius:16px; text-align:center; margin:1rem 0; background:linear-gradient(135deg, {bg_color}, {bg_color2}); border:1px solid {border_color};">
        <div style="font-family:'JetBrains Mono',monospace; font-size:72px; font-weight:700; color:{text_color}; margin:0;">{score_emoji} {score}/100</div>
        <div style="font-weight:600; font-size:1.2rem; text-transform:uppercase; letter-spacing:3px; color:{text_color}; margin-top:0.3rem;">Status: {status}</div>
    </div>
    """)
    
    # Summary
    summary = audit_result.get("summary", "No summary available.")
    st.markdown(f"**Executive Summary:** {summary}")
    
    st.divider()
    
    # Findings
    findings = audit_result.get("findings", [])
    if findings:
        st.markdown(f'<div class="section-title">🚩 Findings ({len(findings)})</div>', unsafe_allow_html=True)
        for finding in findings:
            severity = finding.get("severity", "OBSERVATION")
            css_class = f"finding-{severity.lower()}"
            
            severity_emoji = {
                "CRITICAL": "🔴",
                "MAJOR": "🟡", 
                "MINOR": "🔵",
                "OBSERVATION": "⚪"
            }.get(severity, "⚪")
            
            st.markdown(f"""
            <div class="finding-card {css_class}">
                <strong>{severity_emoji} [{finding.get('id', 'F000')}] {severity} — {finding.get('category', 'General')}</strong>
                <span class="finding-label">Observed</span>
                <span class="finding-value">{finding.get('observation', 'N/A')}</span>
                <span class="finding-label">SOP Requires</span>
                <span class="finding-value">{finding.get('sop_requirement', 'N/A')}</span>
                <span class="finding-label">Discrepancy</span>
                <span class="finding-value">{finding.get('discrepancy', 'N/A')}</span>
                <span class="finding-label">Impact</span>
                <span class="finding-value">{finding.get('impact', 'N/A')}</span>
                <span class="finding-label">Recommended Action</span>
                <span class="finding-value">{finding.get('recommendation', 'N/A')}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No findings — all observations align with SOP requirements.")
    
    st.divider()
    
    # SOP Compliance Checklist
    checklist = audit_result.get("sop_compliance_checklist", [])
    if checklist:
        st.markdown('<div class="section-title">✅ SOP Compliance Checklist</div>', unsafe_allow_html=True)
        for item in checklist:
            status_icon = {
                "COMPLIANT": "✅",
                "NON-COMPLIANT": "❌",
                "UNABLE TO ASSESS": "❓"
            }.get(item.get("status", ""), "❓")
            st.markdown(f"{status_icon} **{item.get('criterion', 'N/A')}** — {item.get('notes', '')}")
    
    st.divider()
    
    # Risk Assessment
    risk = audit_result.get("risk_assessment", "")
    if risk:
        st.markdown('<div class="section-title">⚠️ Risk Assessment</div>', unsafe_allow_html=True)
        st.markdown(risk)
    
    # Recommended Actions
    actions = audit_result.get("recommended_actions", [])
    if actions:
        st.markdown('<div class="section-title">📋 Recommended Actions</div>', unsafe_allow_html=True)
        for i, action in enumerate(actions, 1):
            st.markdown(f"{i}. {action}")
    
    st.divider()
    
    # Raw AI Analysis (collapsible - for transparency)
    with st.expander("🔍 View Raw Image Analysis (Nemotron Vision Output)"):
        st.text(image_analysis)
    
    with st.expander("🔍 View Raw Audit Response (Nemotron Reasoning Output)"):
        st.text(audit_response)

# ---- FOOTER ----
st.html("""
<div style="text-align:center; padding:2rem 0 1rem; font-family:'DM Sans',sans-serif;">
    <div style="margin-bottom:12px;">
        <a href="https://github.com/YOUR-USERNAME/labsentinel" style="background:rgba(118,185,0,0.12); border:1px solid rgba(118,185,0,0.3); color:#76b900; padding:0.6rem 2rem; border-radius:8px; font-weight:700; font-size:1rem; text-decoration:none; display:inline-block;">⭐ View on GitHub</a>
    </div>
    <div style="font-size:0.8rem; color:#404050; margin-top:12px;">
        Powered by NVIDIA Nemotron · Built for <span style="color:#76b900;">GTC 2026</span> Golden Ticket Contest
    </div>
</div>
""")
