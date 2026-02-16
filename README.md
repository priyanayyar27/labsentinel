# 🔬 LabSentinel

<div align="center">

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=700&size=28&pause=1000&color=76B900&center=true&vCenter=true&width=1200&lines=Built+entirely+on+NVIDIA+Nemotron.;The+%231+FDA+violation+is+data+integrity.+This+catches+it.)](https://github.com/priyanayyar27/labsentinel)

</div>

**AI that audits lab images against SOPs to flag compliance gaps in seconds — built entirely on the NVIDIA AI stack.**

[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM_API-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> 🏆 **Built for the [NVIDIA GTC 2026 Golden Ticket Developer Contest](https://developer.nvidia.com/gtc-golden-ticket-contest)**

---

## 💊 The Problem

The pharmaceutical industry spends **$50 billion per year** on regulatory compliance. Lab image audits — verifying that experiment photos match Standard Operating Procedures — are still **100% manual**. A human looks at each image, reads the SOP, writes a finding, and signs off. This takes **10–40 days per batch**, with **70% of QA effort** spent reviewing documentation instead of investigating actual problems.

Meanwhile, FDA enforcement is surging:

| What's Happening | The Number | Source |
|---|---|---|
| FDA compliance failures cost pharma | **$12M+ avg** per event, up to **$1B** under consent decree | [GMP Pros, 2025](https://gmppros.com/pharma-regulatory-compliance/) |
| CDER warning letters surged in FY2025 | **+50%** year-over-year | [CDER Dir. of Compliance via RAPS, Dec 2025](https://insider.thefdagroup.com/p/cder-warning-letters-jump-50-percent) |
| Warning letters citing data integrity | **61%** — the #1 most common violation | [European Pharmaceutical Review, FDA data](https://www.europeanpharmaceuticalreview.com/news/219951/fda-warning-letters-highlight-data-integrity-issues/) |
| Warning letters Jul–Dec 2025 vs 2024 | **+73%** enforcement surge | [Reed Smith, Dec 2025](https://www.reedsmith.com/articles/fda-inspections-in-2025-heightened-rigor-data-driven-targeting-and-increased-surveillance/) |
| Right-first-time production rate | Only **47%** — more than half of batches need rework | [BioPharm International, Dec 2025](https://www.biopharminternational.com/view/review-exception-connecting-dots-faster-batch-release) |

**The gap:** AI in pharma today focuses on drug discovery, document management, and manufacturing-line inspection. No existing product takes lab-generated images — culture plates, chromatograms, gel photos, environmental monitoring — and automatically audits them against the governing SOP to generate compliance findings. That workflow remains 100% manual. LabSentinel fills that gap.

---

## 🎯 What LabSentinel Does

**Upload → Audit → Act**

1. **Upload** a lab image (cell assay, gel electrophoresis, chromatogram, colony plate)
2. **Select** the Standard Operating Procedure for that experiment
3. **LabSentinel audits automatically:**
   - 🔬 Analyzes the image with **Nemotron Nano VL** (Vision)
   - 🧠 Compares observations against SOP with **Nemotron 3 Nano** (Reasoning)
   - 🚩 Flags discrepancies with severity ratings (Critical / Major / Minor / Observation)
   - 📊 Scores compliance on a deterministic 0–100 scale
   - 🔄 Detects image-SOP mismatches in code and overrides the score
   - ✅ Generates a full SOP compliance checklist
   - 📋 Produces a downloadable PDF audit report

**Supports 4 experiment types out of the box:**

| Experiment | SOP Protocol | What LabSentinel Checks |
|---|---|---|
| **Cell Viability (MTT)** | SOP-CV-001 | Purple formazan intensity, well uniformity, contamination, edge effects |
| **Gel Electrophoresis** | SOP-GE-001 | Band sharpness, DNA ladder presence, gel integrity, lane separation |
| **HPLC Chromatography** | SOP-HP-001 | Peak symmetry, baseline stability, retention times, resolution |
| **Colony Counting (CFU)** | SOP-BC-001 | Colony morphology, plate contamination, countable range, dilution accuracy |

*These four were selected because they produce visually auditable outputs, span the full drug development pipeline, and are among the most frequently cited in FDA warning letters — more experiment types can be added via custom SOP paste or by extending the SOP library.*

---

## 🏗️ Architecture

```
                         ┌─────────────────────────────────────────┐
                         │           NVIDIA NIM API                │
                         │         (build.nvidia.com)              │
                         └──────┬──────────────────┬──────────────┘
                                │                  │
                    ┌───────────▼──────┐  ┌───────▼───────────┐
 ┌──────────┐      │  Nemotron Nano   │  │  Nemotron 3 Nano  │
 │ Lab Image │─────▶│  VL (Vision)     │  │  (Reasoning)      │
 │ (upload)  │      │                  │  │                   │
 └──────────┘      │  "I see cloudy   │  │  Compares vision  │
                    │   wells, uneven  │──▶  output vs. SOP   │
                    │   staining..."   │  │  requirements     │
 ┌──────────┐      └──────────────────┘  └────────┬──────────┘
 │ SOP Text  │─────────────────────────────────────┘
 │ (protocol)│                                     │
 └──────────┘                              ┌───────▼──────────┐
                                           │  AUDIT ENGINE    │
                    ┌─────────────────┐    │                  │
                    │ 2-Signal        │    │  • Phantom filter │
                    │ Mismatch Gate   │───▶│  • Deterministic │
                    │                 │    │    scoring       │
                    │ • Vision class  │    │  • Mismatch      │
                    │ • Keywords      │    │    override      │
                    └─────────────────┘    └───────┬──────────┘
                                                   │
                                           ┌───────▼──────────┐
                                           │  AUDIT REPORT    │
                                           │                  │
                                           │  Score: 29/100   │
                                           │  Status: FAIL    │
                                           │  Findings + PDF  │
                                           └──────────────────┘
```

---

## ⚡ NVIDIA Technology Stack

LabSentinel is built **entirely on the NVIDIA AI platform** — no other LLM providers, no OpenAI, no Google.

| NVIDIA Technology | Role in LabSentinel | Why This Model |
|---|---|---|
| **[Nemotron Nano VL](https://build.nvidia.com/nvidia/nemotron-nano-12b-v2-vl)** | Multimodal vision — analyzes lab images | 12B parameter vision-language model optimized for detailed visual reasoning |
| **[Nemotron 3 Nano 30B](https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b)** | Scientific reasoning — compares observations vs. SOP | 30B parameter reasoning model with structured JSON output |
| **[NVIDIA NIM API](https://build.nvidia.com)** | Cloud inference endpoints | Production-ready, OpenAI-compatible API with enterprise reliability |

### Multi-Model Pipeline

Unlike single-model approaches, LabSentinel orchestrates **two specialized Nemotron models** in sequence:

1. **Vision stage** — Nemotron Nano VL classifies the experiment type and describes observations in scientific detail (temperature = 0.0 for determinism)
2. **Reasoning stage** — Nemotron 3 Nano receives the vision output + SOP text, performs structured comparison, and generates a scored audit report in JSON format

This separation ensures each model operates in its area of strength: visual understanding vs. logical reasoning.

---

## 🧠 How The Scoring Works

Pharmaceutical compliance demands reproducible, auditable scores — the same evidence must always produce the same number. LabSentinel achieves this with a **deterministic scoring engine** that calculates scores from structured checklist outputs produced by Nemotron, ensuring consistency across every audit.

### Step 1: Checklist Score

Nemotron evaluates every SOP requirement and marks each one as COMPLIANT, NON-COMPLIANT, or UNABLE TO ASSESS. These are weighted to produce a raw checklist score — compliant items get full credit, unable-to-assess items get partial credit, and non-compliant items get zero.

> **Why partial credit for Unable to Assess?** This follows the FDA's burden-of-proof principle: if you can't *prove* compliance, you're closer to non-compliant than compliant. But it's not the same as confirmed non-compliance. These items represent legitimate sensor gaps — data that requires physical sensors, not photos. This is exactly what our Phase 2 roadmap addresses with NVIDIA Jetson edge AI.

### Step 2: Severity Penalties

Each real finding deducts points based on FDA risk classification — CRITICAL findings (patient safety risk) carry the heaviest penalty, while OBSERVATIONS (best-practice deviations) carry the lightest.

### Step 3: Status Assignment

The final score (checklist score minus penalties, clamped 0–100) determines the status: **PASS** (high compliance), **INVESTIGATE** (review needed), or **FAIL** (non-compliant).

**Same checklist = same score. Every time.** This is critical for audit credibility.

---

## 🛡️ Mismatch Detection & Override

What happens if someone uploads a well plate image but selects the HPLC SOP? LabSentinel catches this automatically using **two independent signals** from the vision model:

1. **Explicit classification** — the vision model's experiment type label
2. **Keyword detection** — domain-specific terms in the description (e.g., "well plate", "chromatogram", "petri dish")

If the detected experiment type doesn't match the SOP → the score is **overridden in code** to reflect the fundamental pairing error, a CRITICAL finding is injected explaining the mismatch, and the status is forced to FAIL. The audit still runs so the user can see exactly what happened.

This override is enforced at the code level, not by the AI prompt — ensuring wrong pairings are always caught regardless of model behavior. Correctly paired audits where some items are "Unable to Assess" (legitimate sensor gaps) are scored fairly and are not affected by this override.

> **Design decision:** Filename-based detection was deliberately excluded. Scientists name files inconsistently (`IMG_4521.jpg`, `tuesday_results.png`), and relying on filenames would introduce false positives.

---

## 🔍 Phantom Finding Filter

The AI sometimes generates findings for things it *cannot see* — "cannot verify column temperature from the image" or "incubation time not visible." These aren't real compliance problems; they're restating that a photo can't show sensor data.

LabSentinel scans each finding for ~30 phrases indicating missing information (e.g., "cannot be verified", "not visible", "image does not show") and removes them — **unless they have CRITICAL or MAJOR severity**, which are always kept as a safety measure.

Without this filter, a single HPLC audit could generate 12 phantom findings, each deducting 5 points, artificially deflating the score by 60 points for things that aren't actually wrong.

---

## 🔎 Additional Features

### Image Quality Gate
Before running the audit, the vision model rates image quality on a 1–10 scale. Images scoring ≤3 are **rejected** — because blurry images produce unreliable audit results, and unreliable results are worse than no results in a compliance context.

### Image Forensics (EXIF Metadata)
LabSentinel extracts and displays EXIF metadata — capture date, camera/device, software, resolution. Verifying that an image was taken on the right date with the right equipment is a core forensic check. Missing EXIF data (common with screenshots or edited images) is flagged.

### Persistent Disk Cache
All AI responses are cached to disk keyed by image hash + SOP hash. Same image + same SOP = identical result forever, even after restart. No wasted API calls, and results are reproducible — a core requirement for compliance tools.

### PDF Audit Report
One-click download of a complete audit report including score, findings, checklist, risk assessment, and image forensics — styled with NVIDIA green branding.

---

## ⚠️ Known Limitations & Honest Design Choices

1. **AI-generated checklist** — The deterministic scoring engine overrides the AI's *number*, but the AI still decides which items are COMPLIANT vs NON-COMPLIANT. If the AI misclassifies a checklist item, the score will be consistently wrong. **Future:** Fine-tuned model on labeled pharmaceutical audit data.

2. **Single-image analysis** — Real SOPs often require multiple images (before/after, control vs. experiment). LabSentinel currently audits one image at a time. **Future:** Multi-image batch upload (Phase 1 roadmap).

3. **No live sensor data** — Requirements like temperature, humidity, and flow rate can't be verified from photos. These show as "Unable to Assess" and receive 25% credit. **Future:** NVIDIA Jetson edge AI for live sensor feeds (Phase 2 roadmap).

4. **4 experiment types** — Currently supports MTT, Gel Electrophoresis, HPLC, and Colony Counting. Custom SOPs can be pasted manually. **Future:** Expanded SOP library + custom SOP upload.

---

## 🚀 Roadmap

| Phase | What | NVIDIA Technology | Goal |
|---|---|---|---|
| **Phase 1 · Scale** | Multi-image batch auditing + auto-generated 21 CFR Part 11 compliance reports | NIM parallel inference | Make it production-ready |
| **Phase 2 · Integrate** | LIMS & e-lab notebook connectors + live sensor feeds (temp, CO₂, humidity) | **NVIDIA Jetson** edge AI | Embed into pharma infrastructure |
| **Phase 3 · Enterprise** | Multi-facility, real-time deployment | **Nemotron Ultra on NVIDIA DGX** | Every QC lab becomes an AI inference node |

**The vision:** Every one of the ~8,000 FDA-registered pharma manufacturing facilities globally generates thousands of lab images per month. Today, a human reviews each one. LabSentinel turns every QC lab into a node in an AI inference network — each image is one inference call, running on NVIDIA hardware.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- NVIDIA API key (free from [build.nvidia.com](https://build.nvidia.com))

### Setup (3 minutes)

```bash
# Clone the repo
git clone https://github.com/priyanayyar27/labsentinel.git
cd labsentinel

# Install dependencies
pip install -r requirements.txt

# Add your NVIDIA API key
cp .env.example .env
# Edit .env and paste your key from build.nvidia.com

# Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Get Your Free NVIDIA API Key

1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Sign in with your NVIDIA account (free)
3. Navigate to any Nemotron model
4. Click "Get API Key"
5. Copy the key starting with `nvapi-`

---

## 📁 Project Structure

```
labsentinel/
├── app.py                  # Main application — UI + audit engine + scoring logic
├── sample_sops.py          # 4 realistic pharmaceutical SOPs
├── requirements.txt        # Python dependencies
├── .env.example            # Template for API key
├── .gitignore              # Excludes .env, cache, __pycache__
├── README.md               # This file
└── samples/                # Sample lab images to try immediately
    ├── hplc_chromatogram.png
    ├── gel_electrophoresis.jpg
    ├── colony_plate.jpg
    └── mtt_well_plate.jpg
```

---

## 🧪 Try It Yourself (Sample Images Included)

Don't have lab images handy? No problem — the [`/samples`](samples/) folder includes test images for every supported experiment type:

| File | Experiment Type | Try pairing with | Expected behavior |
|---|---|---|---|
| `hplc_chromatogram.png` | HPLC | HPLC Chromatography Analysis ✅ | Correct pairing — scores based on visible peaks, flags unknown peaks |
| `gel_electrophoresis.jpg` | Gel | Gel Electrophoresis Quality Check ✅ | Correct pairing — checks band sharpness, ladder presence |
| `colony_plate.jpg` | CFU | Bacterial Colony Counting ✅ | Correct pairing — evaluates colony morphology, countable range |
| `mtt_well_plate.jpg` | MTT | Cell Viability Assay ✅ | Correct pairing — assesses well uniformity, color intensity |
| `mtt_well_plate.jpg` | MTT | HPLC Chromatography Analysis ❌ | **Wrong pairing** — mismatch override triggers, score capped at ≤15 |

> **💡 Tip:** Upload any image with any SOP to test the mismatch detection. The system will catch wrong pairings and explain why.

---

## 👩‍💻 About the Builder

Built by **Priyanka Nayyar** — 3 years at **GSK Pharma** · Scaled product $0→$10M at **Rocket Internet** · MBA (Singapore Management University) + MSBA-STEM (University of California, Davis).

I built LabSentinel because I saw the problem firsthand: data integrity is the **#1 FDA violation** (cited in 61% of warning letters), yet the audit workflow hasn't changed in decades. A human looks at a photo, reads an SOP, writes a finding, signs off. AI in pharma today focuses on drug discovery and manufacturing-line inspection — nobody is automating the lab-level image audit. This is that tool.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/priyankaa-nayyar)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-100000?style=flat-square&logo=github)](https://github.com/priyanayyar27)

---

## 🏷️ GitHub Topics

If you're exploring this repo, here are the topics that describe it: `nvidia`, `nemotron`, `gtc2026`, `golden-ticket-contest`, `pharmaceutical`, `compliance`, `data-integrity`, `computer-vision`, `ai`, `streamlit`, `sop-auditing`

> *These are also set as repository topics on GitHub for discoverability.*

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**#NVIDIAGTC** · Built entirely on NVIDIA Nemotron · Solving the #1 FDA violation: data integrity

[![NVIDIA GTC 2026](https://img.shields.io/badge/NVIDIA_GTC_2026-Golden_Ticket_Contest-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://developer.nvidia.com/gtc-golden-ticket-contest)

</div>




