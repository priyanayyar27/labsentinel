"""
LabSentinel v55 - AI-Powered Lab Data Integrity Auditor
Uses NVIDIA Nemotron models to cross-reference lab imagery against SOPs
and flag data integrity discrepancies in pharmaceutical R&D.
"""

import streamlit as st
import base64
import os
import json
import re
import hashlib
from io import BytesIO
from datetime import datetime
from openai import OpenAI  # NVIDIA NIM API is OpenAI-compatible by design (per NVIDIA docs)
from dotenv import load_dotenv
from sample_sops import SAMPLE_SOPS

# Optional: PIL for EXIF metadata extraction
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ============================================================
# SETUP: Load API key and configure NVIDIA API client
# ============================================================

# Load the .env file (for local development)
load_dotenv()

# Get the API key — works on both local (.env) and Streamlit Cloud (st.secrets)
try:
    NVIDIA_API_KEY = st.secrets["NVIDIA_API_KEY"]
except (KeyError, FileNotFoundError):
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
# HELPER: Extract EXIF metadata from uploaded image
# ============================================================
# Real data integrity audits check image timestamps, camera info,
# and modification history. This extracts what's available.

def extract_exif_metadata(uploaded_file):
    """Extract EXIF metadata from an uploaded image file."""
    metadata = {}
    if not HAS_PIL:
        return metadata
    try:
        uploaded_file.seek(0)
        img = Image.open(BytesIO(uploaded_file.read()))
        uploaded_file.seek(0)  # Reset for later use
        
        # Basic image info
        metadata["image_width"] = img.size[0]
        metadata["image_height"] = img.size[1]
        metadata["format"] = img.format or "Unknown"
        metadata["mode"] = img.mode
        
        # EXIF data (if present — camera photos have it, screenshots usually don't)
        exif_data = img._getexif() if hasattr(img, '_getexif') and img._getexif() else {}
        
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
                metadata["capture_date"] = str(value)
            elif tag_name == "Make":
                metadata["camera_make"] = str(value)
            elif tag_name == "Model":
                metadata["camera_model"] = str(value)
            elif tag_name == "Software":
                metadata["software"] = str(value)
            elif tag_name == "ImageDescription":
                metadata["description"] = str(value)
    except Exception:
        pass
    return metadata


# ============================================================
# HELPER: Generate PDF audit report
# ============================================================
# Exports the full audit results as a downloadable PDF for
# regulatory documentation and record-keeping.

def generate_pdf_report(audit_result, image_quality_score, exif_metadata, score, status):
    """Generate a PDF audit report from the audit results."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    
    def safe_text(text):
        """Strip non-latin-1 characters to prevent fpdf crashes."""
        if not text:
            return "N/A"
        replacements = {
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00b7": "-",
            "\u2022": "-", "\u00b1": "+/-", "\u00b0": " deg", "\u2265": ">=",
            "\u2264": "<=", "\u00d7": "x",
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text.encode("latin-1", errors="replace").decode("latin-1")
    
    def write_text(pdf_obj, text, font_size=10, bold=False):
        """Safely write text to PDF, truncating if needed."""
        style = "B" if bold else ""
        pdf_obj.set_font("Helvetica", style, font_size)
        clean = safe_text(str(text))
        # Truncate very long text to prevent overflow
        if len(clean) > 500:
            clean = clean[:497] + "..."
        try:
            pdf_obj.multi_cell(w=0, h=5, text=clean)
        except Exception:
            # Last resort: truncate further
            try:
                pdf_obj.multi_cell(w=0, h=5, text=clean[:200] + "...")
            except Exception:
                pdf_obj.cell(0, 5, "[Text could not be rendered]", ln=True)
    
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "LabSentinel Audit Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Powered by NVIDIA Nemotron", ln=True, align="C")
    pdf.ln(8)
    
    # Score
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Score: {score}/100  |  Status: {status}", ln=True)
    pdf.ln(4)
    
    # Score Breakdown
    checklist = audit_result.get("sop_compliance_checklist", [])
    n_c = sum(1 for i in checklist if i.get("status", "").upper() == "COMPLIANT")
    n_nc = sum(1 for i in checklist if i.get("status", "").upper() == "NON-COMPLIANT")
    n_ua = sum(1 for i in checklist if i.get("status", "").upper() == "UNABLE TO ASSESS")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Score Breakdown", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Compliant: {n_c}  |  Non-Compliant: {n_nc}  |  Unable to Assess: {n_ua}", ln=True)
    pdf.ln(4)
    
    # Executive Summary
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    write_text(pdf, audit_result.get("summary", "No summary available."))
    pdf.ln(4)
    
    # Findings
    findings = audit_result.get("findings", [])
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Findings ({len(findings)})", ln=True)
    if findings:
        for f in findings:
            write_text(pdf, f"[{f.get('id', 'F000')}] {f.get('severity', 'N/A')} - {f.get('category', 'N/A')}", font_size=10, bold=True)
            write_text(pdf, f"Observed: {f.get('observation', 'N/A')}", font_size=9)
            write_text(pdf, f"SOP Requires: {f.get('sop_requirement', 'N/A')}", font_size=9)
            write_text(pdf, f"Discrepancy: {f.get('discrepancy', 'N/A')}", font_size=9)
            write_text(pdf, f"Recommendation: {f.get('recommendation', 'N/A')}", font_size=9)
            pdf.ln(3)
    else:
        write_text(pdf, "No findings - all observations align with SOP requirements.")
    pdf.ln(4)
    
    # SOP Compliance Checklist
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "SOP Compliance Checklist", ln=True)
    for item in checklist:
        status_mark = {"COMPLIANT": "[PASS]", "NON-COMPLIANT": "[FAIL]", "UNABLE TO ASSESS": "[N/A]"}.get(item.get("status", ""), "[?]")
        write_text(pdf, f"{status_mark} {item.get('criterion', 'N/A')} - {item.get('notes', '')}", font_size=9)
    pdf.ln(4)
    
    # Risk Assessment
    risk = audit_result.get("risk_assessment", "")
    if risk:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Risk Assessment", ln=True)
        write_text(pdf, risk)
    pdf.ln(4)
    
    # Image Forensics
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Image Forensics", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if image_quality_score is not None:
        pdf.cell(0, 6, f"Image Quality: {image_quality_score}/10", ln=True)
    if exif_metadata.get("image_width"):
        pdf.cell(0, 6, f"Resolution: {exif_metadata['image_width']} x {exif_metadata['image_height']} px", ln=True)
    if exif_metadata.get("capture_date"):
        pdf.cell(0, 6, f"Capture Date: {safe_text(str(exif_metadata['capture_date']))}", ln=True)
    
    return bytes(pdf.output())


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
    ]
    
    prompt_text = """You are an expert pharmaceutical laboratory analyst with 20 years 
of experience in quality control and GMP compliance. Analyze this laboratory image in precise scientific detail.

FIRST, identify the experiment type. State ONE of these on the very first line:
EXPERIMENT_TYPE: MTT_CELL_VIABILITY (if you see a multi-well plate with purple/blue colored wells)
EXPERIMENT_TYPE: GEL_ELECTROPHORESIS (if you see a gel slab with bands/lanes, OR a rectangular translucent block under UV/blue light with fluorescent bands, OR an agarose/polyacrylamide gel image)
EXPERIMENT_TYPE: HPLC_CHROMATOGRAPHY (if you see a chromatogram chart with peaks on an x-y axis)
EXPERIMENT_TYPE: COLONY_COUNTING (if you see petri dishes with bacterial/fungal colonies on agar)
EXPERIMENT_TYPE: OTHER (if none of the above — use this ONLY if the image clearly does not match any category)

SECOND, rate the image quality for audit purposes on the next line:
IMAGE_QUALITY: <1-10> (1=completely unusable, 5=marginal, 10=perfect lab documentation quality)
Consider: focus/sharpness, lighting, resolution, framing, whether key details are visible.

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
due to confirmation bias or time pressure.

STEP 1 - EXPERIMENT TYPE CHECK:
First, verify the image shows the same type of experiment as the SOP describes.
- A well plate image should only be audited against a cell viability/MTT SOP
- A chromatogram should only be audited against an HPLC SOP
- A gel image should only be audited against a gel electrophoresis SOP
- A petri dish image should only be audited against a colony counting SOP
If the experiment types DO NOT match (e.g., well plate image vs HPLC SOP), mark ALL checklist 
items as NON-COMPLIANT and add one CRITICAL finding explaining the type mismatch. Then stop.

STEP 2 - IF EXPERIMENT TYPES MATCH, perform the audit with these severity guidelines:
- CRITICAL: Only for issues that directly endanger patient safety or completely invalidate results 
  (e.g., confirmed contamination, data fabrication evidence, wrong experiment type)
- MAJOR: Issues that compromise data reliability but don't invalidate everything 
  (e.g., missing documentation, procedural shortcuts)
- MINOR: Issues that reduce confidence but results may still be usable 
  (e.g., image quality limitations, minor formatting gaps)
- OBSERVATION: Cosmetic or best-practice suggestions

IMPORTANT CALIBRATION:
- An image being a photograph of a printout is at most a MINOR documentation issue, not MAJOR
- If you cannot assess a criterion from the image alone, mark it UNABLE TO ASSESS — do NOT 
  mark it NON-COMPLIANT just because the image doesn't show that specific data
- Labeled peaks in a chromatogram are expected compounds, not "unknown peaks" — only flag 
  truly unidentified or unlabeled peaks
- Be fair: a real-world auditor would not fail an experiment just because a photo doesn't 
  show every instrument parameter

Always respond with the structured JSON format requested. Be specific about 
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
Generate a comprehensive audit report in the following JSON format.

CRITICAL INSTRUCTION FOR CHECKLIST:
The SOP above contains numbered "EXPECTED OBSERVATIONS" and bulleted "REJECTION CRITERIA".
You MUST create exactly ONE checklist item for EACH expected observation and EACH rejection criterion listed in the SOP.
Do NOT invent new checklist items. Do NOT skip any items from the SOP.
For each item, assess ONLY based on what is visible in the image analysis:
- COMPLIANT: Image evidence clearly satisfies this criterion
- NON-COMPLIANT: Image evidence clearly violates this criterion  
- UNABLE TO ASSESS: Image does not provide enough information to evaluate this criterion
When in doubt, use UNABLE TO ASSESS rather than NON-COMPLIANT.

CRITICAL INSTRUCTION FOR FINDINGS:
Findings should ONLY be created for genuine problems visible in the image — things that are 
clearly wrong, contaminated, missing, or deviant from the SOP.
Do NOT create findings for items marked UNABLE TO ASSESS. If you cannot verify something 
from the image, that is a checklist limitation, NOT a finding.
A photograph of a printout is NOT a finding — it is a documentation format.
Limit findings to genuine, visible discrepancies. Most correct experiment images should have 
0-3 findings at most.

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
            "criterion": "<exact criterion from SOP — one per EXPECTED OBSERVATION and REJECTION CRITERION>",
            "status": "<COMPLIANT | NON-COMPLIANT | UNABLE TO ASSESS>",
            "notes": "<brief explanation of what you see or why you can't assess>"
        }}
    ],
    "risk_assessment": "<brief paragraph on overall risk to data integrity>",
    "recommended_actions": ["<action 1>", "<action 2>", "<action 3>"]
}}

Be thorough but fair. Only flag genuine concerns, not speculative issues.
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
    
    # ---- FINDINGS FILTER ----
    # The AI often generates findings for things it CANNOT see in the image
    # (e.g., "cannot verify temperature", "incubation time not visible").
    # These are not real findings — they're just restating UNABLE TO ASSESS items.
    # We filter them out deterministically so they don't inflate the penalty.
    
    # Keywords that indicate a finding is about missing info, not a real problem
    not_real_finding_phrases = [
        "cannot be verified", "cannot be assessed", "cannot be determined",
        "cannot be confirmed", "cannot be evaluated", "cannot be measured",
        "cannot confirm", "cannot assess", "cannot determine", "cannot evaluate",
        "not visible", "not provided", "not shown", "not available",
        "not displayed", "not indicated", "not present in the image",
        "does not show", "does not display", "does not indicate",
        "does not provide", "lacks visible", "lacks context",
        "image does not", "image lacks", "from the image alone",
        "from a static image", "from the static image",
        "from the captured image", "from the current image",
        "printed on paper", "scanned", "photographed",
    ]
    
    filtered_findings = []
    for f in findings:
        # Combine all text fields to check for phantom finding phrases
        finding_text = " ".join([
            str(f.get("observation", "")),
            str(f.get("discrepancy", "")),
            str(f.get("impact", "")),
        ]).lower()
        
        # Keep the finding only if it describes a REAL visible problem
        is_phantom = any(phrase in finding_text for phrase in not_real_finding_phrases)
        
        # Always keep CRITICAL and MAJOR findings — even if phrased poorly, they matter
        if f.get("severity", "").upper() in ["CRITICAL", "MAJOR"]:
            filtered_findings.append(f)
        elif not is_phantom:
            filtered_findings.append(f)
    
    # Update results with filtered findings
    result["findings"] = filtered_findings
    findings = filtered_findings
    
    if checklist:
        compliant = sum(1 for item in checklist if item.get("status", "").upper() == "COMPLIANT")
        non_compliant = sum(1 for item in checklist if item.get("status", "").upper() == "NON-COMPLIANT")
        unable = sum(1 for item in checklist if item.get("status", "").upper() == "UNABLE TO ASSESS")
        total = compliant + non_compliant + unable
        
        if total > 0:
            # Compliant items get full marks.
            # Unable-to-assess gets 25% credit — in pharma, if you can't prove compliance,
            # you're closer to non-compliant than compliant (FDA burden-of-proof principle).
            raw_score = ((compliant * 1.0) + (unable * 0.25)) / total * 100
            
            # Deduct points for findings by severity.
            # Weights mapped to FDA risk classification: CRITICAL = patient safety risk,
            # MAJOR = regulatory non-compliance, MINOR = procedural gap, OBSERVATION = cosmetic.
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
    /* Fix Streamlit icon text leak on sidebar toggle */
    button[data-testid="stBaseButton-headerNoPadding"] {
        font-size: 0 !important;
    }
    /* Fix Streamlit expander icon text leak */
    details[data-testid="stExpander"] summary span[class*="emotion-cache"] {
        overflow: hidden;
    }
    .stat-row {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
        align-items: baseline;
    }
    .stat-number {
        font-family: 'JetBrains Mono', monospace !important;
        color: #76b900;
        font-weight: 700;
        font-size: 0.95rem;
        min-width: 64px;
        flex-shrink: 0;
    }
    .stat-text {
        color: #8a8a96;
        font-size: 0.92rem;
    }
    .stat-source {
        display: block;
        margin-top: 2px;
        font-size: 0.72rem;
        color: #5a5a6a;
        font-style: italic;
    }
    .stat-source a {
        color: #5a8a30;
        text-decoration: none;
    }
    .stat-source a:hover {
        text-decoration: underline;
        color: #76b900;
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
    
    /* Download button — NVIDIA green with bold white text */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #76b900, #5a8f00) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(118, 185, 0, 0.25) !important;
        color: #ffffff !important;
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
    <div style="font-size:22px; color:#b0b0c0; font-weight:500; margin-bottom:16px;">AI that audits lab images against SOPs to flag compliance gaps in seconds.</div>
    <div style="display:flex; gap:2rem; flex-wrap:wrap; align-items:center;">
        <span style="font-size:13px; color:#606070; font-family:'JetBrains Mono',monospace;">⚡ <span style="color:#76b900;">Nemotron Nano VL</span> — <span style="color:#d0d0dc;">Vision</span></span>
        <span style="font-size:13px; color:#606070; font-family:'JetBrains Mono',monospace;">🧠 <span style="color:#76b900;">Nemotron 3 Nano</span> — <span style="color:#d0d0dc;">Reasoning</span></span>
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
        <div style="font-size:13px; color:#9090a0; line-height:1.5;">3 years at <span style="color:#d0d0dc; font-weight:600;">GSK Pharma</span> · Scaled product $0→$10M at <span style="color:#d0d0dc; font-weight:600;">Rocket Internet</span> · Built this to solve the <span style="color:#d0d0dc; font-weight:600;">#1 FDA violation:</span> <span style="color:#d0d0dc; font-weight:600;">data integrity</span>.</div>
    </div>
    """)
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">🧪 Why This Matters</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-number">$50B</span><span class="stat-text">global pharma compliance spend · lab image audits still manual<span class="stat-source"><a href="https://gmppros.com/pharma-regulatory-compliance/" target="_blank">McKinsey Healthcare Analytics 2024 via GMP Pros</a></span></span></div>
    <div class="stat-row"><span class="stat-number">+50%</span><span class="stat-text">surge in CDER warning letters FY2025<span class="stat-source"><a href="https://insider.thefdagroup.com/p/cder-warning-letters-jump-50-percent" target="_blank">Jill Furman, CDER Dir. of Compliance, Dec 2025 via RAPS</a></span></span></div>
    <div class="stat-row"><span class="stat-number">61%</span><span class="stat-text">of FDA warning letters cite data integrity — #1 violation<span class="stat-source"><a href="https://www.europeanpharmaceuticalreview.com/news/219951/fda-warning-letters-highlight-data-integrity-issues/" target="_blank">European Pharmaceutical Review, FDA data</a></span></span></div>
    <div class="stat-row"><span class="stat-number">$12M+</span><span class="stat-text">avg cost per compliance failure · up to $1B under consent decree<span class="stat-source"><a href="https://gmppros.com/pharma-regulatory-compliance/" target="_blank">GMP Pros 2025</a> · consent decree public records</span></span></div>
    """, unsafe_allow_html=True)

    st.divider()

    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">⚡ What LabSentinel Saves</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-number">10–40d</span><span class="stat-text">batch visual audit → seconds with AI-assisted review<span class="stat-source"><a href="https://www.biopharminternational.com/view/review-exception-connecting-dots-faster-batch-release" target="_blank">BioPharm International, Dec 2025</a></span></span></div>
    <div class="stat-row"><span class="stat-number">70%</span><span class="stat-text">of QA effort spent reviewing docs, not investigating<span class="stat-source"><a href="https://www.ey.com/en_us/insights/life-sciences/electronic-batch-records-improve-pharma-manufacturing" target="_blank">EY Life Sciences, 2025</a></span></span></div>
    <div class="stat-row"><span class="stat-number">47%</span><span class="stat-text">right-first-time rate — LabSentinel catches errors in real time<span class="stat-source"><a href="https://www.biopharminternational.com/view/review-exception-connecting-dots-faster-batch-release" target="_blank">BioPharm International, Dec 2025</a></span></span></div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">📋 How It Works</div>')
    st.markdown("""
    <div class="stat-row"><span class="stat-number">1.</span><span class="stat-text">Upload a lab image from your experiment</span></div>
    <div class="stat-row"><span class="stat-number">2.</span><span class="stat-text">Select the matching SOP protocol</span></div>
    <div class="stat-row"><span class="stat-number">3.</span><span class="stat-text">Click audit — AI flags discrepancies in seconds</span></div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.html('<div style="font-family:JetBrains Mono,monospace; font-size:1.1rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:2px; margin-bottom:10px;">🚀 Roadmap</div>')
    st.markdown("""
    <div style="margin-bottom:14px;">
        <div style="font-size:1.05rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px;">Phase 1 · Scale</div>
        <div style="color:#d0d0dc; font-size:0.95rem; line-height:1.5;">🔄 Multi-image batch auditing<br>📋 Auto-generated 21 CFR Part 11 compliance reports</div>
    </div>
    <div style="border-top:1px solid rgba(118,185,0,0.15); margin-bottom:14px; padding-top:12px;">
        <div style="font-size:1.05rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px;">Phase 2 · Integrate</div>
        <div style="color:#d0d0dc; font-size:0.95rem; line-height:1.5;">🏥 LIMS & e-lab notebook connectors<br>🌡️ Live sensor feeds (temp, CO₂, humidity) via <span style="color:#76b900; font-weight:600;">NVIDIA Jetson</span> edge AI</div>
    </div>
    <div style="border-top:1px solid rgba(118,185,0,0.15); margin-bottom:8px; padding-top:12px;">
        <div style="font-size:1.05rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px;">Phase 3 · Enterprise</div>
        <div style="color:#d0d0dc; font-size:0.95rem; line-height:1.5;">⚡ <span style="color:#76b900; font-weight:600;">Nemotron Ultra on NVIDIA DGX</span> for multi-facility, real-time deployment</div>
    </div>
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
    
    # Determine image type safely
    if uploaded_image.type and "/" in uploaded_image.type:
        image_type = uploaded_image.type
    else:
        image_type = "image/jpeg"
    
    # Convert image to base64
    image_b64 = image_to_base64(uploaded_image)
    
    # Create a unique hash for this image to use as cache key
    image_hash = hashlib.sha256(image_b64.encode()).hexdigest()
    
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
    
    # STEP 1.25: Extract EXIF metadata for forensic audit trail
    exif_metadata = extract_exif_metadata(uploaded_image)
    
    # STEP 1.5a: Image Quality Gate
    # Extract the IMAGE_QUALITY rating from the vision model's response
    image_quality_score = None
    for line in image_analysis.split('\n')[:5]:
        if "IMAGE_QUALITY:" in line.upper():
            try:
                image_quality_score = int(re.search(r'\d+', line.split(":")[-1]).group())
            except (AttributeError, ValueError):
                pass
            break
    
    # Block audit if image quality is too low to produce reliable results
    if image_quality_score is not None and image_quality_score <= 3:
        st.html("""
        <div style="padding:2rem; border-radius:16px; text-align:center; margin:1rem 0; background:linear-gradient(135deg, rgba(255,176,32,0.12), rgba(255,176,32,0.03)); border:1px solid rgba(255,176,32,0.4);">
            <div style="font-family:'JetBrains Mono',monospace; font-size:72px; font-weight:700; color:#ffb020; margin:0;">⚠️ LOW QUALITY IMAGE</div>
            <div style="font-weight:600; font-size:1.2rem; text-transform:uppercase; letter-spacing:3px; color:#ffb020; margin-top:0.3rem;">Image quality too low for reliable audit</div>
        </div>
        """)
        st.warning(f"**Image quality rated {image_quality_score}/10 by the vision model.** "
                   "The image is too blurry, dark, or low-resolution for a reliable audit. "
                   "Please upload a clearer image and try again. "
                   "A quality score of 4 or higher is required to proceed.")
        st.stop()
    
    # STEP 1.5b: Check if image matches the selected SOP
    # Uses TWO vision-based signals (filename intentionally excluded — scientists use arbitrary names)
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
        "GEL_ELECTROPHORESIS": ["gel electrophoresis", "agarose", "gel band", "dna gel", "gel lane", "electrophoresis", "uv light", "uv illuminat", "fluorescent band", "ethidium bromide", "translucent block", "transparent block", "dna ladder", "gel slab"],
        "HPLC_CHROMATOGRAPHY": ["hplc", "chromatogram", "chromatography", "retention time", "peak area"],
        "COLONY_COUNTING": ["colony count", "cfu", "petri dish", "bacterial colony", "agar plate"],
    }
    
    # SIGNAL 1: What experiment type did the vision model explicitly classify?
    detected_type = "OTHER"
    for line in image_analysis.split('\n')[:3]:
        if "EXPERIMENT_TYPE:" in line.upper():
            detected_type = line.split(":")[-1].strip().upper()
            break
    
    # SIGNAL 2: Check the vision description text for strong keywords
    description_lower = image_analysis.lower()
    description_type = "OTHER"
    for exp_type, keywords in type_keywords.items():
        if any(kw in description_lower for kw in keywords):
            description_type = exp_type
            break
    
    # Combine signals: use the best available classification
    # Priority: explicit vision classification > description keywords
    # NOTE: Filename is intentionally excluded — scientists use arbitrary naming
    # conventions, and relying on filenames would create false mismatches
    best_detected_type = detected_type
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
    
    # NOTE: We no longer block the audit on mismatch. The audit always runs,
    # and the score-based warning (≤20) handles both mismatch AND genuine failures.
    # Hard-blocking was too aggressive — a low score on a "mismatched" pair could
    # still be a valid audit of a genuinely failed experiment.
    
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
    
    # ---- MISMATCH SCORE OVERRIDE ----
    # If code-level mismatch detection found a wrong pairing (e.g., well plate vs HPLC SOP),
    # override the score regardless of what Nemotron returned. The model often marks mismatched
    # criteria as UNABLE TO ASSESS instead of NON-COMPLIANT, inflating the score.
    # Legitimate "unable to assess" (e.g., can't read temperature from photo) only applies
    # when the experiment type MATCHES the SOP — sensor gaps, not experiment mismatches.
    if is_mismatch:
        audit_result["data_integrity_score"] = min(audit_result.get("data_integrity_score", 0), 15)
        audit_result["overall_status"] = "FAIL"
        # Add a mismatch finding if one doesn't already exist
        existing_findings = audit_result.get("findings", [])
        has_mismatch_finding = any("mismatch" in f.get("category", "").lower() or "mismatch" in f.get("discrepancy", "").lower() for f in existing_findings)
        if not has_mismatch_finding:
            existing_findings.insert(0, {
                "id": "F000",
                "severity": "CRITICAL",
                "category": "Experiment Type Mismatch",
                "observation": f"Vision model detected: {best_detected_type}",
                "sop_requirement": f"SOP expects: {expected_type}",
                "discrepancy": "The uploaded image does not match the selected SOP protocol. This is a fundamental pairing error, not a compliance failure.",
                "impact": "Audit results are not meaningful when image and SOP are from different experiment types.",
                "recommendation": "Select the correct SOP for this image, or upload the correct image for this SOP."
            })
            audit_result["findings"] = existing_findings
    
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
    
    # ---- SCORE BREAKDOWN VISUAL ----
    checklist_display = audit_result.get("sop_compliance_checklist", [])
    findings_display = audit_result.get("findings", [])
    n_compliant = sum(1 for item in checklist_display if item.get("status", "").upper() == "COMPLIANT")
    n_non_compliant = sum(1 for item in checklist_display if item.get("status", "").upper() == "NON-COMPLIANT")
    n_unable = sum(1 for item in checklist_display if item.get("status", "").upper() == "UNABLE TO ASSESS")
    n_total = n_compliant + n_non_compliant + n_unable
    
    # Calculate penalty for display
    severity_penalties_display = {"CRITICAL": 15, "MAJOR": 10, "MINOR": 5, "OBSERVATION": 2}
    total_penalty = sum(severity_penalties_display.get(f.get("severity", "").upper(), 0) for f in findings_display)
    
    # Bar widths (percentage)
    pct_compliant = round(n_compliant / n_total * 100) if n_total > 0 else 0
    pct_non_compliant = round(n_non_compliant / n_total * 100) if n_total > 0 else 0
    pct_unable = round(n_unable / n_total * 100) if n_total > 0 else 0
    
    raw_score_display = round(((n_compliant * 1.0) + (n_unable * 0.25)) / n_total * 100) if n_total > 0 else 0
    
    st.html(f"""
    <div style="padding:1.2rem 1.5rem; border-radius:12px; margin:0.5rem 0 1rem; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06);">
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; font-weight:700; color:#76b900; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px;">📊 Score Breakdown</div>
        <div style="display:flex; height:24px; border-radius:6px; overflow:hidden; margin-bottom:10px; background:#1a1a24;">
            <div style="width:{pct_compliant}%; background:#4cdf78;" title="Compliant"></div>
            <div style="width:{pct_non_compliant}%; background:#ff4d5e;" title="Non-Compliant"></div>
            <div style="width:{pct_unable}%; background:#555;" title="Unable to Assess"></div>
        </div>
        <div style="display:flex; gap:1.5rem; flex-wrap:wrap; font-size:0.85rem; margin-bottom:8px;">
            <span style="color:#4cdf78;">✅ Compliant: {n_compliant}/{n_total}</span>
            <span style="color:#ff4d5e;">❌ Non-Compliant: {n_non_compliant}/{n_total}</span>
            <span style="color:#888;">❓ Unable to Assess: {n_unable}/{n_total}</span>
        </div>
        <div style="font-size:0.82rem; color:#707080; font-family:'JetBrains Mono',monospace; line-height:1.8;">
            Checklist Score: {raw_score_display}/100 &nbsp;·&nbsp; Finding Penalties: −{total_penalty} pts &nbsp;·&nbsp; <span style="color:{text_color}; font-weight:600;">Final: {score}/100</span>
        </div>
    </div>
    """)
    
    # Possible SOP mismatch OR serious compliance failure warning
    if score <= 40:
        # Check if the vision model detected a different experiment type than the SOP expects
        mismatch_note = ""
        if is_mismatch:
            mismatch_note = ' <strong style="color:#ff6b7a;">The AI detected a different experiment type than the selected SOP — this is likely an incorrect pairing.</strong>'
        
        st.html(f"""
        <div style="padding:1.2rem; border-radius:12px; margin:0.5rem 0 1rem; background:rgba(255,176,32,0.08); border:1px solid rgba(255,176,32,0.3);">
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:700; color:#ffb020; text-transform:uppercase; letter-spacing:1.5px;">⚠️ Unusually Low Score</div>
            <div style="color:#b0b0c0; font-size:0.95rem; margin-top:6px;">A score this low typically indicates one of two things: <strong style="color:#ffffff;">(1)</strong> the uploaded image does not match the selected SOP — please verify you chose the correct protocol, or <strong style="color:#ffffff;">(2)</strong> a serious compliance failure was detected in the experiment. Review the findings below carefully.{mismatch_note}</div>
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
    
    # Image Forensics (EXIF metadata + quality score)
    st.markdown('<div class="section-title">🔎 Image Forensics</div>', unsafe_allow_html=True)
    
    forensic_col1, forensic_col2 = st.columns(2)
    with forensic_col1:
        quality_label = "Unknown"
        quality_color = "#8a8a96"
        if image_quality_score is not None:
            if image_quality_score >= 7:
                quality_label = f"{image_quality_score}/10 — Good"
                quality_color = "#4cdf78"
            elif image_quality_score >= 4:
                quality_label = f"{image_quality_score}/10 — Marginal"
                quality_color = "#ffd44a"
            else:
                quality_label = f"{image_quality_score}/10 — Poor"
                quality_color = "#ff6b7a"
        st.markdown(f"**Image Quality:** <span style='color:{quality_color}'>{quality_label}</span>", unsafe_allow_html=True)
        if exif_metadata.get("image_width"):
            st.markdown(f"**Resolution:** {exif_metadata['image_width']} × {exif_metadata['image_height']} px")
        if exif_metadata.get("format"):
            st.markdown(f"**Format:** {exif_metadata['format']} ({exif_metadata.get('mode', 'N/A')})")
    
    with forensic_col2:
        if exif_metadata.get("capture_date"):
            st.markdown(f"**Capture Date:** {exif_metadata['capture_date']}")
        else:
            st.markdown("**Capture Date:** Not available (no EXIF data)")
        if exif_metadata.get("camera_make") or exif_metadata.get("camera_model"):
            camera = f"{exif_metadata.get('camera_make', '')} {exif_metadata.get('camera_model', '')}".strip()
            st.markdown(f"**Camera/Device:** {camera}")
        if exif_metadata.get("software"):
            st.markdown(f"**Software:** {exif_metadata['software']}")
    
    st.divider()
    
    # ---- PDF EXPORT ----
    st.markdown('<div class="section-title">📄 Export Report</div>', unsafe_allow_html=True)
    pdf_bytes = generate_pdf_report(audit_result, image_quality_score, exif_metadata, score, status)
    if pdf_bytes:
        st.download_button(
            label="📥 Download Audit Report (PDF)",
            data=pdf_bytes,
            file_name=f"LabSentinel_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.info("PDF export requires the `fpdf2` package. Install with: `pip install fpdf2`")
    


# ---- FOOTER ----
st.html("""
<div style="text-align:center; padding:2rem 0 1rem; font-family:'DM Sans',sans-serif;">
    <div style="margin-bottom:12px;">
        <a href="https://github.com/priyanayyar27/labsentinel" style="background:rgba(118,185,0,0.12); border:1px solid rgba(118,185,0,0.3); color:#76b900; padding:0.6rem 2rem; border-radius:8px; font-weight:700; font-size:1rem; text-decoration:none; display:inline-block;">⭐ View on GitHub</a>
    </div>
    <div style="font-size:0.8rem; color:#404050; margin-top:12px;">
        Powered by NVIDIA Nemotron · Built for <span style="color:#76b900;">GTC 2026</span> Golden Ticket Contest
    </div>
</div>
""")
