# 🔬 LabSentinel

### Catches data integrity issues that human auditors miss.

**An AI-powered pharmaceutical data integrity auditor that cross-references lab imagery against Standard Operating Procedures — built entirely on the NVIDIA AI stack.**

[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM_API-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> 🏆 **Built for the [NVIDIA GTC 2026 Golden Ticket Developer Contest](https://developer.nvidia.com/gtc-golden-ticket-contest)**

---

## 💊 The Problem

Pharmaceutical data integrity failures are a **$28 billion/year crisis** — and it's getting worse.

| Statistic | Source |
|-----------|--------|
| **$28B/year** wasted on irreproducible preclinical research in the US alone | [Freedman et al., PLOS Biology](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1002165) |
| **50%+** of preclinical studies cannot be replicated | [Nature, 2012](https://www.nature.com/articles/483531a) |
| **+50% jump** in FDA warning letters in 2025 — data integrity is the #1 cited issue | FDA Inspection Database |
| **$800M–$1.4B** cost of a single failed Phase 3 clinical trial | [DiMasi et al.](https://doi.org/10.1016/j.jhealeco.2016.01.012) |
| Amgen replicated 53 landmark cancer studies — **only 11% succeeded** | [Begley & Ellis, Nature](https://www.nature.com/articles/483531a) |

**The root cause?** Human auditors suffer from confirmation bias, time pressure, and fatigue. They review lab results expecting them to be correct — and miss subtle discrepancies between what the lab actually produced and what the protocol required.

**LabSentinel replaces manual spot-checks with AI-powered systematic auditing.**

---

## 🎯 What LabSentinel Does

LabSentinel is an AI auditor that cross-references **physical lab evidence** (images) against **digital protocols** (SOPs) to flag data integrity issues — in seconds, not hours.

**Upload → Audit → Act**

1. **Upload** a lab image (cell assay, gel electrophoresis, chromatogram, colony plate)
2. **Select** the Standard Operating Procedure for that experiment
3. **LabSentinel audits automatically:**
   - 🔬 Analyzes the image with **Nemotron Nano VL** (vision model)
   - 🧠 Compares observations against SOP with **Nemotron 3 Nano** (reasoning model)
   - 🚩 Flags discrepancies with severity ratings (Critical / Major / Minor)
   - 📊 Scores data integrity on a deterministic 0–100 scale
   - ✅ Generates an SOP compliance checklist
   - 📋 Recommends corrective actions

**Supports 4 experiment types out of the box:**
- Cell Viability Assay (MTT Protocol)
- Gel Electrophoresis Quality Check
- HPLC Chromatography Analysis
- Bacterial Colony Counting (CFU Assay)

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
                    │ 3-Signal        │    │  • Parse JSON    │
                    │ Mismatch Gate   │───▶│  • Deterministic │
                    │                 │    │    scoring       │
                    │ • Vision class  │    │  • Severity map  │
                    │ • Filename      │    │  • Compliance    │
                    │ • Keywords      │    │    checklist     │
                    └─────────────────┘    └───────┬──────────┘
                                                   │
                                           ┌───────▼──────────┐
                                           │  AUDIT REPORT    │
                                           │                  │
                                           │  Score: 42/100   │
                                           │  Status: INVEST. │
                                           │  3 Findings      │
                                           │  5 Actions       │
                                           └──────────────────┘
```

---

## ⚡ NVIDIA Technology Stack

LabSentinel is built **entirely on the NVIDIA AI platform** — no other LLM providers, no OpenAI, no Google.

| NVIDIA Technology | Role in LabSentinel | Why This Model |
|-------------------|--------------------|-----------------------|
| **[Nemotron Nano VL](https://build.nvidia.com/nvidia/nemotron-nano-12b-v2-vl)** | Multimodal vision — analyzes lab images | 12B parameter vision-language model optimized for detailed visual reasoning |
| **[Nemotron 3 Nano 30B](https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b)** | Scientific reasoning — compares observations vs. SOP | 30B parameter reasoning model with structured JSON output |
| **[NVIDIA NIM API](https://build.nvidia.com)** | Cloud inference endpoints | Production-ready, OpenAI-compatible API with enterprise reliability |

### Multi-Model Pipeline

Unlike single-model approaches, LabSentinel orchestrates **two specialized Nemotron models** in sequence:

1. **Vision stage** — Nemotron Nano VL classifies the experiment type and describes observations in scientific detail (temperature = 0.0 for determinism)
2. **Reasoning stage** — Nemotron 3 Nano receives the vision output + SOP text, performs structured comparison, and generates a scored audit report in JSON format

This separation ensures each model operates in its area of strength: visual understanding vs. logical reasoning.

---

## 🧠 Technical Innovation

### Deterministic Scoring Algorithm

AI models are notoriously inconsistent with numerical scores. Ask the same question twice, get two different numbers. **That's unacceptable for a compliance tool.**

LabSentinel solves this with a **deterministic scoring engine** that overrides the AI's subjective score:

```python
# Score is CALCULATED from checklist, not trusted from the AI
raw_score = ((compliant * 1.0) + (unable * 0.5)) / total * 100

# Severity-based penalty deductions
severity_penalties = {"CRITICAL": 15, "MAJOR": 10, "MINOR": 5, "OBSERVATION": 2}
penalty = sum(penalties for each finding)

final_score = max(0, min(100, round(raw_score - penalty)))
```

**Same checklist = same score. Every time.** This is critical for audit credibility.

### 3-Signal Mismatch Detection

Before running the expensive reasoning model, LabSentinel validates that the uploaded image actually matches the selected SOP using three independent signals:

1. **Vision classification** — the vision model's explicit `EXPERIMENT_TYPE` label
2. **Filename analysis** — keywords in the uploaded file name
3. **Description keywords** — domain-specific terms in the vision output

If signals indicate a mismatch (e.g., gel image + MTT protocol), the audit is blocked immediately — saving API cost and preventing misleading results.

### Persistent Disk Cache

All AI responses are cached to disk (`.labsentinel_cache.json`) keyed by image hash + SOP hash. This means:
- Same image + same SOP = identical result forever (even after restart)
- No wasted API calls on repeated audits
- Results are reproducible — a core requirement for any compliance tool

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
├── app.py              # Main application (UI + audit logic)
├── sample_sops.py      # 4 realistic pharmaceutical SOPs
├── requirements.txt    # Python dependencies
├── .env.example        # Template for API key
├── .gitignore          # Excludes .env, cache, __pycache__
└── README.md           # This file
```

---

## 🔮 Roadmap

This MVP demonstrates the core audit loop. The full vision:

| Phase | Feature | NVIDIA Technology |
|-------|---------|-------------------|
| **v2** | Multi-image batch auditing | NIM parallel inference |
| **v2** | Raw instrument data analysis (CSV/Excel) | Nemotron 3 Nano |
| **v3** | LIMS & electronic lab notebook integration | NIM microservices |
| **v3** | Auto-generated regulatory PDF reports | Nemotron document generation |
| **v4** | **On-premise deployment for pharma data sovereignty** | **NVIDIA DGX** |
| **v4** | Production-grade accuracy with larger models | **Nemotron Ultra** |

The ultimate vision: an **autonomous compliance agent** that continuously monitors lab data streams — images, instrument files, electronic notebooks — running on **NVIDIA DGX infrastructure** inside pharma facilities where data sovereignty is non-negotiable. Nemotron's efficient model architecture makes on-premise deployment viable even for mid-size Contract Research Organizations (CROs).

---

## 🧪 Supported Experiment Types

| Experiment | SOP Protocol | What LabSentinel Checks |
|-----------|-------------|------------------------|
| **Cell Viability (MTT)** | SOP-CV-001 | Purple formazan intensity, well uniformity, contamination, edge effects |
| **Gel Electrophoresis** | SOP-GE-001 | Band sharpness, DNA ladder presence, gel integrity, lane separation |
| **HPLC Chromatography** | SOP-HP-001 | Peak symmetry, baseline stability, retention times, resolution |
| **Colony Counting (CFU)** | SOP-BC-001 | Colony morphology, plate contamination, countable range, dilution accuracy |

---

## 👩‍💻 About the Builder

Built by **Priyanka Nayyar** — a product and marketing leader with experience at **GSK, Agoda (Booking Holdings), and Rocket Internet**, now pursuing an MSBA at UC Davis.

This project addresses a problem I saw up close in the pharmaceutical industry: flawed lab data surviving through pipeline stages, wasting resources, and ultimately failing in late-stage clinical trials. LabSentinel brings AI-powered rigor to a process that has relied on manual spot-checks for decades.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/priyankaa-nayyar)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-100000?style=flat-square&logo=github)](https://github.com/priyanayyar27)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**#NVIDIAGTC** · Built entirely on NVIDIA Nemotron · Addressing the $28B/year reproducibility crisis

[![NVIDIA GTC 2026](https://img.shields.io/badge/NVIDIA_GTC_2026-Golden_Ticket_Contest-76b900?style=for-the-badge&logo=nvidia&logoColor=white)](https://developer.nvidia.com/gtc-golden-ticket-contest)

</div>
