# sample_sops.py
# This file contains example Standard Operating Procedures (SOPs) for lab experiments.
# These are realistic protocols that the AI will compare against lab images.

SAMPLE_SOPS = {
    "Cell Viability Assay (MTT Protocol)": """
STANDARD OPERATING PROCEDURE: MTT Cell Viability Assay
Protocol ID: SOP-CV-001
Version: 3.2

OBJECTIVE:
Assess cell viability and proliferation using the MTT colorimetric assay.

EXPECTED OBSERVATIONS:
1. Wells with viable cells should show PURPLE/VIOLET coloration after MTT reduction.
2. Dead cell wells (positive control) should remain YELLOW/CLEAR with no purple color.
3. Color intensity should be UNIFORM across replicate wells (±10% variation acceptable).
4. No visible contamination: wells must be FREE of cloudiness, floating particles, or film.
5. Edge wells may show slight evaporation but should not differ by more than 15% from center wells.
6. Media should be CLEAR before MTT addition — any turbidity suggests contamination.

CRITICAL PARAMETERS:
- Incubation temperature: 37°C ± 0.5°C
- CO2 concentration: 5% ± 0.2%
- MTT incubation time: 3-4 hours (do NOT exceed 5 hours)
- Cell seeding density: 5,000-10,000 cells per well (96-well plate)
- Absorbance reading: 570nm (reference wavelength: 630nm)

REJECTION CRITERIA:
- Any well showing bacterial or fungal contamination (cloudiness, color change in media)
- Coefficient of variation >20% among replicate wells
- Negative control wells showing purple coloration (indicates assay reagent issue)
- Plate left outside incubator for >15 minutes during any step
""",

    "Gel Electrophoresis Quality Check": """
STANDARD OPERATING PROCEDURE: Agarose Gel Electrophoresis QC
Protocol ID: SOP-GE-002
Version: 2.1

OBJECTIVE:
Verify DNA/RNA fragment separation and integrity via agarose gel electrophoresis.

EXPECTED OBSERVATIONS:
1. DNA ladder bands should be SHARP, DISTINCT, and evenly spaced according to marker specifications.
2. Sample bands should show CLEAR separation with minimal smearing.
3. Wells should be INTACT — no torn or deformed wells visible.
4. Background should be DARK and UNIFORM with minimal non-specific fluorescence.
5. Bands should run STRAIGHT — any curvature indicates uneven gel casting or buffer issues.
6. No bright spots or streaking in lanes (indicates DNA degradation or overloading).
7. Loading dye front should be visible and consistent across all lanes.

CRITICAL PARAMETERS:
- Agarose concentration: 1.0% for standard DNA (0.8% for large fragments, 2% for small)
- Running buffer: 1X TAE or 1X TBE (must match gel preparation buffer)
- Voltage: 80-120V (5-8 V/cm gel length)
- Running time: 30-60 minutes (until dye front reaches 75% of gel length)
- Staining: Ethidium bromide (0.5 µg/mL) or SYBR Safe equivalent

REJECTION CRITERIA:
- Smeared bands indicating DNA/RNA degradation
- Lane-to-lane migration inconsistency >10%
- Absence of expected bands in positive control lane
- Gel showing cracks, air bubbles, or uneven thickness
- Overloaded lanes showing merged or indistinct bands
""",

    "HPLC Chromatography Analysis": """
STANDARD OPERATING PROCEDURE: HPLC Purity Analysis
Protocol ID: SOP-HP-003
Version: 4.0

OBJECTIVE:
Determine compound purity and identify impurities via High-Performance Liquid Chromatography.

EXPECTED OBSERVATIONS:
1. Main compound peak should be SHARP and SYMMETRIC (tailing factor 0.8-1.5).
2. Baseline should be STABLE and FLAT with minimal drift (<0.001 AU/min).
3. Peak resolution between main compound and nearest impurity should be >1.5.
4. Retention time for main peak should match reference standard ± 2%.
5. No ghost peaks or carryover from previous injections in blank runs.
6. System suitability criteria: RSD of peak areas <2.0% for replicate injections.

CRITICAL PARAMETERS:
- Column: C18, 250mm x 4.6mm, 5µm particle size
- Mobile phase: Acetonitrile/Water gradient as specified
- Flow rate: 1.0 mL/min ± 0.01
- Column temperature: 25°C ± 1°C
- Injection volume: 10 µL
- Detection wavelength: 254nm (or compound-specific)
- Run time: 30 minutes minimum

REJECTION CRITERIA:
- Purity <95% for active pharmaceutical ingredient
- Unidentified peaks >0.1% of main peak area
- Baseline noise >0.005 AU
- System suitability failure (RSD >2.0%)
- Retention time shift >5% from reference
- Negative peaks or detector saturation
""",

    "Bacterial Colony Counting (CFU Assay)": """
STANDARD OPERATING PROCEDURE: Colony Forming Unit (CFU) Count
Protocol ID: SOP-BC-004
Version: 2.3

OBJECTIVE:
Quantify viable bacterial colonies to determine antimicrobial efficacy or culture concentration.

EXPECTED OBSERVATIONS:
1. Colonies should be DISCRETE and WELL-SEPARATED (countable range: 30-300 CFU per plate).
2. Colony morphology should be CONSISTENT — uniform size, shape, and color within same strain.
3. Negative control plates should show ZERO colonies (no contamination).
4. Positive control should show expected growth within ±1 log of target concentration.
5. No SPREADING colonies that would obscure accurate counting.
6. Agar surface should be SMOOTH and INTACT — no cracks, drying, or condensation pooling.

CRITICAL PARAMETERS:
- Incubation temperature: 37°C ± 1°C (or organism-specific)
- Incubation time: 18-24 hours (do NOT count before 16 hours)
- Dilution series: 10-fold serial dilutions, minimum 3 replicates per dilution
- Plating method: Spread plate (100 µL) or pour plate (1 mL)
- Media: Mueller-Hinton agar or organism-appropriate media

REJECTION CRITERIA:
- Plates with <30 or >300 colonies (outside countable range)
- Contamination on negative control plates
- Colonies too confluent to count accurately
- Evidence of swarming or spreading growth
- Plates showing signs of dehydration (cracked agar, reduced volume)
- Inconsistent colony counts between replicates (CV >25%)
"""
}
