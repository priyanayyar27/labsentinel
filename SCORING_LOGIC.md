# LabSentinel v55 — Scoring Logic & Match/Mismatch Decision

## Document Purpose

This document explains exactly how LabSentinel calculates the compliance score and decides whether an image-SOP pairing is correct or incorrect. This is the locked logic as of v55. Any future changes must be documented against this baseline.

---

## How The Audit Works (Big Picture)

When a user uploads a lab image and selects an SOP, LabSentinel runs a **two-step process:**

**Step 1 — Vision Analysis (Nemotron Nano VL)**
The vision model looks at the image and describes everything it sees: what type of experiment it is, what equipment is visible, what the results look like, and any anomalies. It also classifies the experiment type (e.g., "this is a well plate" or "this is a chromatogram").

**Step 2 — SOP Comparison (Nemotron 3 Nano)**
The reasoning model takes the vision description from Step 1 and compares it line-by-line against the selected SOP. It produces a structured report with:
- A **checklist** — every SOP requirement marked as COMPLIANT, NON-COMPLIANT, or UNABLE TO ASSESS
- **Findings** — specific problems it detected, each with a severity level
- A summary and risk assessment

After the AI produces its report, LabSentinel's **code** takes over and calculates the final score using a deterministic formula. We do NOT trust the AI's own score — we calculate it ourselves from the checklist and findings, so the same checklist always produces the same number.

---

## The Three Possible Outcomes For Each Checklist Item

Every SOP requirement gets one of three statuses:

### COMPLIANT ✅
The AI can see evidence in the image that this requirement is met.

*Example: SOP says "peaks should be sharp and symmetric." The AI sees sharp, symmetric peaks in the chromatogram. → COMPLIANT.*

### NON-COMPLIANT ❌
The AI can see evidence in the image that this requirement is NOT met.

*Example: SOP says "no unidentified peaks above 0.1% of main peak area." The AI sees a large unknown peak. → NON-COMPLIANT.*

### UNABLE TO ASSESS ❓
The AI cannot determine compliance from the image alone. The information simply isn't visible.

*Example: SOP says "column temperature must be 25°C ± 1°C." The AI is looking at a photo — temperature readings are not visible in the image. → UNABLE TO ASSESS.*

**Why does UNABLE TO ASSESS exist?**

A lab image is a snapshot. It captures what something looks like, but it cannot show measurements like temperature, flow rate, humidity, or timing. These require sensors, which LabSentinel does not have yet (this is Phase 2 of the roadmap — NVIDIA Jetson edge AI for live sensor feeds). Until then, UNABLE TO ASSESS is the honest answer for any requirement that needs data beyond what a photo can show.

---

## Score Calculation Formula

### Step A — Raw Checklist Score

Each checklist item contributes to the raw score based on its status:

| Status | Points | Why |
|---|---|---|
| COMPLIANT | 1.0 (full credit) | Requirement verified as met |
| UNABLE TO ASSESS | 0.25 (25% credit) | Can't verify from image — not a failure, but can't prove compliance either |
| NON-COMPLIANT | 0.0 (zero credit) | Requirement verified as NOT met |

**Formula:**

```
Raw Score = ((COMPLIANT × 1.0) + (UNABLE TO ASSESS × 0.25) + (NON-COMPLIANT × 0.0)) / TOTAL ITEMS × 100
```

**Why does UNABLE TO ASSESS get 25% credit instead of 0% or 50%?**

This follows the FDA's burden-of-proof principle: in pharmaceutical compliance, if you cannot PROVE that a requirement was met, you are closer to non-compliant than compliant. However, it's not the same as confirmed non-compliance. 25% reflects this: it's mostly penalized but acknowledges that the requirement wasn't actually violated — we just can't verify it from a photo.

**Real example (HPLC chromatogram + HPLC SOP — correct pairing):**
- 4 items COMPLIANT, 1 item NON-COMPLIANT, 14 items UNABLE TO ASSESS
- Raw Score = ((4 × 1.0) + (14 × 0.25) + (1 × 0.0)) / 19 × 100
- Raw Score = (4 + 3.5 + 0) / 19 × 100 = 7.5 / 19 × 100 = **39/100**

### Step B — Severity Penalties

If the AI found actual problems (findings), each one deducts points based on how serious it is:

| Severity | Penalty (points deducted) | What it means |
|---|---|---|
| CRITICAL | −15 points | Patient safety risk, data fabrication, wrong experiment type |
| MAJOR | −10 points | Regulatory non-compliance, significant procedural deviation |
| MINOR | −5 points | Procedural gap, documentation issue |
| OBSERVATION | −2 points | Cosmetic issue, minor best-practice deviation |

**Formula:**

```
Final Score = Raw Score − Total Penalties
```

The final score is clamped between 0 and 100 (never goes below 0 or above 100).

**Continuing the real example:**
- 1 finding: MAJOR severity (unknown peak exceeding threshold) = −10 points
- Final Score = 39 − 10 = **29/100**

### Step C — Status Assignment

The final score determines the overall status:

| Score Range | Status | What it means |
|---|---|---|
| 80–100 | PASS ✅ | Compliant — no significant issues detected |
| 50–79 | INVESTIGATE ⚠️ | Review needed — some concerns but not definitive failure |
| 0–49 | FAIL ❌ | Non-compliant — significant issues or insufficient evidence of compliance |

**Continuing the real example:**
- Final Score = 29/100 → **FAIL** ❌

---

## Phantom Finding Filter

Before calculating the score, LabSentinel removes "phantom findings" — these are findings the AI generates about things it CANNOT see, not things it actually found wrong.

**The problem:** The AI sometimes creates findings like "Cannot verify column temperature from the image" or "Incubation time not visible in the photograph." These aren't real compliance problems — they're just restating that the image doesn't contain certain information (which is already captured by the UNABLE TO ASSESS status in the checklist).

**How the filter works:** LabSentinel scans each finding's text for phrases that indicate it's about missing information rather than a real problem:

- "cannot be verified", "cannot be assessed", "not visible", "not provided"
- "does not show", "image does not", "from a static image"
- And ~30 similar phrases

If a finding matches any of these phrases, it is removed — UNLESS it has CRITICAL or MAJOR severity. Critical and Major findings are always kept, even if phrased poorly, because they indicate something serious enough that it's better to over-report than under-report.

**Why this matters:** Without this filter, an HPLC audit might generate 12 findings like "cannot verify column temperature" — each one a MINOR or OBSERVATION severity. That would deduct 5 × 12 = 60 points from the score for things that aren't actually wrong. The filter prevents this artificial score deflation.

---

## Match/Mismatch Detection

This is the system that catches when someone uploads the wrong image for the selected SOP (e.g., a well plate photo paired with an HPLC SOP).

### How It Detects a Mismatch

LabSentinel uses two signals to determine what experiment the image shows:

**Signal 1 — Explicit Classification**
The vision model is instructed to state the experiment type on the first line of its analysis (e.g., "EXPERIMENT_TYPE: MTT_CELL_VIABILITY"). If present, this is the strongest signal.

**Signal 2 — Keyword Detection**
If Signal 1 isn't clear, LabSentinel scans the vision description for strong keywords:
- Well plate, microplate, 96-well, formazan → **MTT Cell Viability**
- Gel, agarose, DNA ladder, gel band → **Gel Electrophoresis**
- Chromatogram, HPLC, retention time, peak area → **HPLC Chromatography**
- Petri dish, colony, CFU, agar plate → **Colony Counting**

The code then checks: does the detected experiment type match what the selected SOP expects?

**Decision rule:**
- If the detected type is specific (not "OTHER") AND it doesn't match the SOP's expected type → **MISMATCH**
- If the detected type is "OTHER" (couldn't determine) → no mismatch flagged (benefit of the doubt)
- If they match → no mismatch

**What is NOT used:** Filenames. Scientists use arbitrary naming conventions for their image files, so relying on filenames would create false mismatches.

### What Happens When a Mismatch Is Detected

This is the critical safety net added in v55. When `is_mismatch = True`:

1. **Score is capped at ≤15** — regardless of what the AI's checklist produced
2. **Status is forced to FAIL** — no matter what
3. **A CRITICAL finding is injected** explaining the mismatch:
   - What the vision model detected (e.g., "well plate")
   - What the SOP expected (e.g., "HPLC chromatography")
   - Clear explanation that this is a pairing error, not a compliance failure

**Why is this done in code instead of relying on the AI?**

The AI prompt already instructs Nemotron: "If experiment types DO NOT match, mark ALL checklist items as NON-COMPLIANT." However, Nemotron (a 30B parameter model) doesn't reliably follow this instruction. When given a mismatched pair, it often marks items as UNABLE TO ASSESS instead of NON-COMPLIANT — which inflates the score through the 0.25 partial credit.

By enforcing the mismatch penalty in code, we guarantee that wrong pairings always score ≤15, regardless of AI behavior.

**Why ≤15 and not 0?**

Using `min(current_score, 15)` means if the AI already calculated a score below 15, we keep the lower score. If it calculated higher (which is the problem), we cap it at 15. This prevents the override from accidentally raising a score that was already appropriately low.

### Why This Design Is Fair

The mismatch override and the UNABLE TO ASSESS partial credit work together:

| Scenario | UNABLE TO ASSESS Credit | Mismatch Override | Result |
|---|---|---|---|
| **Correct pairing, sensor gaps** (e.g., HPLC image + HPLC SOP, but can't read temperature) | 0.25 per item ✅ | Not triggered ✅ | Fair score reflecting what CAN be verified |
| **Wrong pairing** (e.g., well plate + HPLC SOP) | Would inflate score ⚠️ | Caps at ≤15 ✅ | Honest low score for wrong pairing |

This means a correctly paired audit isn't penalized for sensor gaps (legitimate limitation until Phase 2), while a wrongly paired audit can't game the system through UNABLE TO ASSESS inflation.

---

## Complete Score Calculation Pipeline (Summary)

```
1. Vision model analyzes image → describes what it sees + classifies experiment type
2. Code checks: does image experiment type match SOP type?
   → If no: flag is_mismatch = True
   → If yes or unclear: continue normally
3. Reasoning model compares vision analysis against SOP → produces checklist + findings
4. Phantom finding filter removes fake findings (keeps CRITICAL/MAJOR)
5. Raw Score calculated: (COMPLIANT × 1.0 + UNABLE × 0.25) / TOTAL × 100
6. Severity penalties deducted from raw score
7. Final Score = Raw Score − Penalties (clamped 0–100)
8. If is_mismatch: override Final Score to ≤15, force FAIL, inject mismatch finding
9. Status assigned: ≥80 PASS, ≥50 INVESTIGATE, <50 FAIL
```

---

## Supported Experiment Types (v55)

| Experiment Type | Sample SOP Available | Image Keywords |
|---|---|---|
| MTT Cell Viability | ✅ SOP-CV | well plate, microplate, 96-well, formazan, purple well |
| Gel Electrophoresis | ✅ SOP-GE | gel, agarose, DNA ladder, gel band, UV light |
| HPLC Chromatography | ✅ SOP-HP | chromatogram, HPLC, retention time, peak area |
| Colony Counting (CFU) | ✅ SOP-BC | petri dish, colony, CFU, agar plate, bacterial colony |

---

## Legend / Dictionary

| Term | Simple Explanation |
|---|---|
| **SOP** | Standard Operating Procedure — a step-by-step document that tells lab workers exactly how to perform a test |
| **Checklist** | A list of every requirement from the SOP, each marked as compliant, non-compliant, or unable to assess |
| **Finding** | A specific problem the AI detected — something that doesn't match what the SOP requires |
| **Severity** | How serious a finding is: CRITICAL (worst) → MAJOR → MINOR → OBSERVATION (least serious) |
| **Phantom Finding** | A fake finding where the AI reports "can't see X" as a problem, when really it's just a limitation of the image |
| **Mismatch** | When the uploaded image shows a completely different experiment than what the selected SOP is for |
| **Raw Score** | The score calculated from the checklist before any penalties are subtracted |
| **Penalty** | Points deducted for each real finding, based on its severity |
| **Final Score** | Raw Score minus penalties — this is the number shown to the user |
| **Deterministic** | Always produces the same output from the same input — no randomness |
| **Nemotron Nano VL** | NVIDIA's vision-language AI model — it can "see" images and describe them |
| **Nemotron 3 Nano** | NVIDIA's reasoning AI model — it compares text descriptions against SOPs |
| **HPLC** | High-Performance Liquid Chromatography — a lab technique to separate and measure chemical compounds |
| **MTT** | A lab test that measures how many cells are alive in a sample, using color change in a well plate |
| **Gel Electrophoresis** | A lab technique that separates DNA/RNA/protein fragments by size using an electric field through a gel |
| **CFU** | Colony Forming Units — a way to count bacteria by growing them on a plate and counting visible clusters |
| **21 CFR Part 11** | FDA regulation governing electronic records and electronic signatures in pharmaceutical manufacturing |
| **FDA burden-of-proof** | In pharma compliance, the manufacturer must PROVE they followed procedures — the FDA doesn't have to prove they didn't |
| **Clamped** | A value that's forced to stay within a range (e.g., never below 0 or above 100) |
| **Cache** | Stored results from previous runs — if the same image + SOP combination is tested again, the stored result is used instead of re-running the AI |
| **Temperature 0.0** | An AI setting that makes the model's output as consistent as possible (less random) |

---

## Version History

| Version | Scoring Change |
|---|---|
| app_approved_copy | Unable to Assess = 0.5 (50% credit), no phantom filter, no mismatch detection |
| v48 | Unable to Assess = 0.25 (25% credit), phantom filter added, mismatch prompt instruction added (but model doesn't follow it reliably) |
| v49–v54 | No scoring changes (cosmetic only) |
| **v55 (current, locked)** | Code-level mismatch override added: wrong pairings capped at ≤15, FAIL forced, CRITICAL finding injected. Scoring formula unchanged from v48. |
