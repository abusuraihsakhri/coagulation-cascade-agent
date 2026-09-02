# Coagulation Cascade Agent

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Coagulation Cascade Agent** is an advanced analytical and computational platform implementing Prolonged aPTT Mixing Study, Factor Assay & Lupus Anticoagulant Arbiter.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`interpret_pt()`**: Interpret Prothrombin Time (PT).

Args:
    pt_seconds: PT in seconds

Returns:
    Dict with status, interpretation, and possible causes
- **`interpret_inr()`**: Interpret INR (International Normalized Ratio).

Args:
    inr: INR value
    therapeutic_context: 'warfarin_standard', 'warfarin_mechanical_valve', or None

Returns:
    Dict with status, interpretation, and therapeutic assessment
- **`interpret_aptt()`**: Interpret Activated Partial Thromboplastin Time (aPTT).

Args:
    aptt_seconds: Patient aPTT in seconds
    control_aptt: Control/normal aPTT for ratio calculation
    heparin_monitoring: Whether this is for heparin therapy monitoring

Returns:
    Dict with status, interpretation, and therapeutic assessment
- **`interpret_mixing_study()`**: Interpret aPTT mixing study.

A mixing study mixes patient plasma 1:1 with normal pooled plasma.

Immediate mix:
  - If corrects (within normal or within 10% of control): factor deficiency likely
  - If does not correct: inhibitor likely (lupus anticoagulant, specific factor inhibitor)

2-hour incubation:
  - If prolongs after incubation: factor inhibitor (e.g., Factor VIII inhibitor)
  - If stays corrected: factor deficiency confirmed
  - LA typically does not correct on immediate mix

Rosner Index = |aPTT mix - aPTT control| / aPTT patient × 100
  - < 10%: correction (factor deficiency)
  - ≥ 10%: no correction (inhibitor)

Args:
    patient_aptt: Patient's aPTT (seconds)
    immediate_mix_aptt: aPTT of 1:1 immediate mix (seconds)
    incubated_mix_aptt: aPTT of 1:1 mix after 2-hour incubation (seconds)
    control_aptt: Normal pooled plasma aPTT (seconds)

Returns:
    Dict with mixing study interpretation
- **`identify_factor_deficiency()`**: Identify likely factor deficiency from PT/aPTT pattern.

Patterns:
  - PT prolonged, aPTT normal → Factor VII deficiency (extrinsic pathway)
  - PT normal, aPTT prolonged → Factor VIII, IX, XI, or XII (intrinsic pathway)
  - Both prolonged → Common pathway (X, V, II, I) or DIC/liver disease
  - Both normal → Consider Factor XIII deficiency, platelet disorder, or vWD

Args:
    pt_seconds: PT in seconds
    aptt_seconds: aPTT in seconds
    thrombin_time: Optional TT in seconds (helps differentiate fibrinogen issues)

Returns:
    Dict with pattern, likely deficiencies, and recommended workup

---

## 📐 Mathematical Formulation & Logic

```text
  Rosner Index = |aPTT mix - aPTT control| / aPTT patient × 100
  rosner_index = abs(immediate_mix_aptt - control_aptt) / patient_aptt * 100
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --pt <value> --inr <value> --context <value> --aptt <value>
```

### Parameter Reference
- `--pt`: Specifies input measurement or parameter value.
- `--inr`: Specifies input measurement or parameter value.
- `--context`: Specifies input measurement or parameter value.
- `--aptt`: Specifies input measurement or parameter value.
- `--control-aptt`: Specifies input measurement or parameter value.
- `--heparin`: Specifies input measurement or parameter value.
- `--patient-aptt`: Specifies input measurement or parameter value.
- `--immediate-mix`: Specifies input measurement or parameter value.
- `--incubated-mix`: Specifies input measurement or parameter value.
- `--indication`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t coagulation-cascade-agent .
docker run -p 8000:8000 coagulation-cascade-agent
```
