# 🔬 LabSentinel — AI-Powered Lab Data Integrity Auditor

**LabSentinel catches pharma data integrity failures at the lab bench — before they become billion-dollar problems.**

Built with NVIDIA Nemotron models for the [GTC 2026 Golden Ticket Contest](https://developer.nvidia.com/gtc-golden-ticket-contest).

---

## The Problem

- **$28 billion/year** is wasted on irreproducible preclinical research in the US alone ([Freedman et al., PLOS Biology](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1002165))
- **50%+** of preclinical studies cannot be replicated
- **FDA warning letters jumped 50% in 2025**, with data integrity as the #1 compliance issue
- A single failed Phase 3 trial costs **$800M–$1.4B**
- Amgen tried to replicate 53 landmark cancer studies — **only 11% succeeded**

The root cause? Human bias, selective reporting, and manual verification that misses discrepancies between what the lab actually produced and what protocols required.

## What LabSentinel Does

LabSentinel is an AI auditor that cross-references **physical lab evidence** (images) against **digital protocols** (SOPs) to detect data integrity issues in real-time.

**The flow:**
1. Upload a lab image (cell assay, gel electrophoresis, chromatogram, colony plate)
2. Select the Standard Operating Procedure (SOP) for that experiment
3. LabSentinel uses NVIDIA Nemotron AI to:
   - **Analyze** the image with multimodal vision AI
   - **Compare** observations against SOP requirements
   - **Flag** discrepancies with severity ratings
   - **Score** overall data integrity (0–100)
   - **Recommend** corrective actions

## Demo

![LabSentinel Demo](screenshot.png)

## Quick Start

### Prerequisites
- Python 3.10+
- NVIDIA API key (free from [build.nvidia.com](https://build.nvidia.com))

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR-USERNAME/labsentinel.git
cd labsentinel

# Install dependencies
pip install -r requirements.txt

# Add your NVIDIA API key
echo "NVIDIA_API_KEY=nvapi-your-key-here" > .env

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## NVIDIA Technology Used

| Technology | Role | Why |
|-----------|------|-----|
| **Nemotron 3 Nano 30B** | Scientific reasoning & SOP comparison | Latest open reasoning model, excels at structured analysis and scientific domains |
| **NVIDIA NIM API** | Cloud inference via build.nvidia.com | Production-ready API endpoints, OpenAI-compatible format |
| **Nemotron Vision** | Lab image analysis | Multimodal understanding of scientific imagery |

All models accessed via [build.nvidia.com](https://build.nvidia.com) API endpoints — no GPU required.

## How It Works

```
┌─────────────────┐    ┌──────────────────────┐    ┌───────────────────────┐
│   Lab Image      │───▶│  Nemotron Vision      │───▶│  Image Analysis       │
│   (upload)       │    │  (multimodal AI)      │    │  "I see cloudy wells, │
└─────────────────┘    └──────────────────────┘    │   uneven staining..." │
                                                    └───────────┬───────────┘
                                                                │
┌─────────────────┐                                             │
│   SOP Protocol   │─────────────────────────────┐              │
│   (text)         │                              │              │
└─────────────────┘                              ▼              ▼
                                        ┌──────────────────────────┐
                                        │  Nemotron 3 Nano         │
                                        │  (reasoning engine)      │
                                        │                          │
                                        │  Compares observations   │
                                        │  vs. SOP requirements    │
                                        └────────────┬─────────────┘
                                                     │
                                                     ▼
                                        ┌──────────────────────────┐
                                        │  AUDIT REPORT            │
                                        │  • Integrity Score: 42   │
                                        │  • Status: INVESTIGATE   │
                                        │  • 3 Findings flagged    │
                                        │  • Corrective actions    │
                                        └──────────────────────────┘
```

## Future Roadmap

This prototype demonstrates the core concept. The full vision includes:

- **Real-time SOP deviation detection** during experiments
- **Automated audit trails** compliant with FDA 21 CFR Part 11
- **Integration with LIMS** (Laboratory Information Management Systems)
- **BioNeMo NIMs** for molecular structure validation
- **Multi-experiment correlation** to detect systematic bias across projects
- **Enterprise deployment** with role-based access for scientists, lab managers, and QA officers

## About the Author

Built by a product and GTM strategist with **10+ years of experience in pharma and healthcare** at GSK, Booking Holdings (Agoda), and Rocket Internet. Currently pursuing an MSBA at UC Davis, combining domain expertise in pharmaceutical R&D with data science and AI to solve real industry problems.

This project addresses a problem I witnessed firsthand: flawed lab data surviving through pipeline stages, wasting resources, and ultimately failing in late-stage clinical trials.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**#NVIDIAGTC** | Built with NVIDIA Nemotron | Addressing the $28B/year reproducibility crisis
