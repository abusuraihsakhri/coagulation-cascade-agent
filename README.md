# Coagulation Cascade Agent

> **Domain:** Hematology / Coagulation & Clinical Decision Support  
> **Standards:** CLSI H54-A (Mixing Studies), ISTH SSC Guidelines (Lupus Anticoagulant & DIC Criteria), CAP Coagulation Checklists

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests: Pytest](https://img.shields.io/badge/Pytest-Passing-brightgreen.svg)](tests/)

---

## 📖 Overview

**Coagulation Cascade Agent** is a comprehensive clinical computational engine and diagnostic arbiter for hematology laboratory profiles. It evaluates:
- **Prothrombin Time (PT)** and **International Normalized Ratio (INR)** for extrinsic pathway integrity and vitamin K antagonist (warfarin) monitoring.
- **Activated Partial Thromboplastin Time (aPTT)** for intrinsic pathway kinetics and unfractionated heparin (UFH) titration.
- **Mixing Studies (1:1 Normal Pooled Plasma)** with immediate and 2-hour 37°C incubation to differentiate factor deficiencies from circulating inhibitors (lupus anticoagulant vs. specific factor inhibitors).
- **Factor Deficiency Differential Diagnosis** mapping extrinsic, intrinsic, and common pathway defects.
- **Disseminated Intravascular Coagulation (DIC)** ISTH scoring algorithms.

---

## 🧬 Coagulation Cascade Pathway Kinetics

The classical coagulation cascade is structured into three convergent pathways:

```
Extrinsic Pathway (Tissue Factor, VII)           Intrinsic Pathway (XII, XI, IX, VIII)
               \                                                  /
                \                                                /
                 v                                              v
           [ PT / INR ]                                    [ aPTT ]
                 \                                              /
                  \                                            /
                   +------------------> [ Common Pathway ] <--+
                                        (X, V, II, I)
                                              |
                                              v
                                   Prothrombin (II) -> Thrombin (IIa)
                                              |
                                              v
                                   Fibrinogen (I)  -> Fibrin Clot
```

### Reference Ranges & Pathway Mapping

| Test | Normal Reference Range | Primary Pathway Evaluated | Critical Coagulation Factors |
| :--- | :--- | :--- | :--- |
| **PT** | 11.0 – 13.5 seconds | Extrinsic & Common | Factor VII, X, V, Prothrombin (II), Fibrinogen (I) |
| **INR** | 0.8 – 1.2 (Target: 2.0–3.0 / 2.5–3.5) | Extrinsic (Warfarin standard) | Factor VII, X, II (Vitamin K-dependent) |
| **aPTT** | 25.0 – 35.0 seconds | Intrinsic & Common | Factors XII, XI, IX, VIII, X, V, II, Fibrinogen |
| **Thrombin Time (TT)** | 14.0 – 19.0 seconds | Fibrinogen Conversion | Fibrinogen quantity/function, Heparin effect |

---

## 🧪 Prolonged aPTT Mixing Study Algorithm

When an unexplained prolongation of aPTT is detected, a **1:1 mixing study** with Normal Pooled Plasma (NPP) is performed immediately and after a 2-hour 37°C incubation.

```
                             Patient aPTT Prolonged (> 35s)
                                           |
                                 Perform 1:1 Mix (NPP)
                                           |
                    +----------------------+----------------------+
                    |                                             |
           Immediate Correction                         No Immediate Correction
          (Rosner Index < 10%)                           (Rosner Index >= 10%)
                    |                                             |
          2-Hour Incubation at 37°C                      Immediate Inhibitor
                    |                                  (Lupus Anticoagulant or Heparin)
         +----------+----------+                                  |
         |                     |                          Order dRVVT Screen/Confirm
    Stays Corrected      Prolongs Again                           Heparin Adsorption
         |                     |
   Factor Deficiency     Time-Dependent Inhibitor
   (VIII, IX, XI, XII)   (e.g., Factor VIII Inhibitor)
         |                     |
  Order Factor Assays   Order Bethesda Assay Titers
```

### Mathematical Indices

#### 1. Rosner Index (Index of Circulating Anticoagulant - ICA)
$$\text{Rosner Index (\%)} = \frac{|\text{aPTT}_{\text{1:1 mix}} - \text{aPTT}_{\text{control}}|}{\text{aPTT}_{\text{patient}}} \times 100$$
- **$< 10.0\%$:** Correction $\rightarrow$ Factor Deficiency.
- **$\ge 10.0\%$:** Lack of correction $\rightarrow$ Inhibitor present.

#### 2. Chang Percent Correction
$$\text{Chang Ratio (\%)} = \frac{\text{aPTT}_{\text{patient}} - \text{aPTT}_{\text{1:1 mix}}}{\text{aPTT}_{\text{patient}} - \text{aPTT}_{\text{control}}} \times 100$$
- **$> 70.0\%$:** Complete correction $\rightarrow$ Factor Deficiency.
- **$< 58.0\%$:** Failure to correct $\rightarrow$ Circulating Inhibitor.

---

## 📊 DIC Diagnostic Criteria (ISTH 2001 Scientific Subcommittee)

Overt Disseminated Intravascular Coagulation (DIC) is calculated based on standard laboratory parameters in patients with an underlying disorder known to cause DIC:

| Diagnostic Parameter | Clinical Laboratory Value | ISTH Points |
| :--- | :--- | :---: |
| **Platelet Count** | $> 100 \times 10^9/\text{L}$ | 0 |
| | $50 - 100 \times 10^9/\text{L}$ | 1 |
| | $< 50 \times 10^9/\text{L}$ | 2 |
| **Elevated Fibrin-Related Markers** (D-Dimer / FDP) | No increase | 0 |
| | Moderate increase | 2 |
| | Strong increase | 3 |
| **Prolonged Prothrombin Time (PT)** | $< 3$ seconds prolongation | 0 |
| | $3 - 6$ seconds prolongation | 1 |
| | $> 6$ seconds prolongation | 2 |
| **Fibrinogen Level** | $> 1.0\text{ g/L}$ | 0 |
| | $< 1.0\text{ g/L}$ | 1 |

$$\text{Total Score} = \sum (\text{Points})$$
- **$\text{Total Score} \ge 5$:** Compatible with **Overt DIC** (repeat score daily).
- **$\text{Total Score} < 5$:** Suggestive of **Non-Overt DIC** (re-evaluate in 24–48 hours).

---

## 💊 Anticoagulation Dosing & Heparin Monitoring Rules

### Warfarin Monitoring (INR Targets)
- **Standard Indications** (DVT/PE, Non-valvular Atrial Fibrillation): Target INR **2.0 – 3.0**.
- **Mechanical Prosthetic Mitral Valve**: Target INR **2.5 – 3.5**.
- **Management of Supratherapeutic INR:**
  - $\text{INR } 4.5 - 10.0$ (no bleeding): Hold 1–2 doses, decrease maintenance dose by 10–20%.
  - $\text{INR } > 10.0$ (no bleeding): Hold warfarin, administer oral vitamin K1 (2.5–5 mg).
  - Serious/life-threatening bleed: Hold warfarin, IV vitamin K1 (10 mg), 4-factor Prothrombin Complex Concentrate (4F-PCC).

### Unfractionated Heparin (UFH) Titration (aPTT Ratio)
$$\text{Ratio} = \frac{\text{Patient aPTT}}{\text{Control aPTT}}$$
- **Therapeutic Target:** $1.5 - 2.5\times$ control baseline.
- **Ratio $< 1.2$:** Bolus 80 units/kg, increase infusion rate by 4 units/kg/hr.
- **Ratio $1.2 - 1.49$:** Increase infusion rate by 2 units/kg/hr.
- **Ratio $1.5 - 2.5$:** Therapeutic. Maintain current infusion rate.
- **Ratio $2.51 - 3.0$:** Decrease infusion rate by 2 units/kg/hr.
- **Ratio $> 3.0$:** Pause infusion for 1 hour, decrease rate by 3 units/kg/hr, monitor for hemorrhage.

---

## 💻 CLI Quickstart

### 1. Prothrombin Time (PT)
```bash
python cli.py pt --pt 16.5
```

### 2. International Normalized Ratio (INR)
```bash
python cli.py inr --inr 2.8 --context warfarin_standard
```

### 3. Activated Partial Thromboplastin Time (aPTT)
```bash
python cli.py aptt --aptt 68.0 --control-aptt 30.0 --heparin
```

### 4. 1:1 Mixing Study Interpretation
```bash
python cli.py mixing --patient-aptt 58.0 --immediate-mix 32.0 --incubated-mix 49.0 --control-aptt 30.0
```

### 5. Factor Deficiency Pattern Identifier
```bash
python cli.py factors --pt 12.0 --aptt 54.0
```

### 6. Warfarin Titration Guidance
```bash
python cli.py warfarin --inr 4.2 --indication standard
```

### 7. Heparin Infusion Adjustment
```bash
python cli.py heparin --aptt 42.0 --control-aptt 30.0
```

### 8. Batch Processing
Process clinical CSV cohort files with automated diagnostics:
```bash
python cli.py batch -i sample.csv -o results.csv
```

---

## 🧪 Verification & Testing

Execute the complete test suite:
```bash
python -m pytest -p no:zarr -v
```

Execute CLI batch smoke test:
```bash
python cli.py batch -i sample.csv -o out_smoke.csv
python -c "import os; assert os.path.exists('out_smoke.csv'); os.remove('out_smoke.csv')"
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
