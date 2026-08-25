# Coagulation Cascade Calculator & Interpreter

A zero-dependency Python tool for interpreting coagulation tests, identifying factor deficiencies, and monitoring anticoagulant therapy.

## Features

### PT/INR Interpretation
- Normal PT: 11–13.5 seconds
- Normal INR: 0.8–1.2
- Classifies as Normal, Shortened, or Prolonged (mild/moderate/severe)

### aPTT Interpretation
- Normal aPTT: 25–35 seconds
- Heparin monitoring: target 1.5–2.5× control

### Mixing Study
- Rosner Index calculation: |aPTT mix − aPTT control| / aPTT patient × 100
- Rosner Index < 10% → correction (factor deficiency)
- Rosner Index ≥ 10% → no correction (inhibitor)
- 2-hour incubation distinguishes time-dependent inhibitors (Factor VIII inhibitor) from immediate-acting inhibitors (LA, heparin)

### Factor Deficiency Pattern Recognition

| PT | aPTT | Pathway | Likely Deficiency |
|----|------|---------|-------------------|
| Prolonged | Normal | Extrinsic | Factor VII |
| Normal | Prolonged | Intrinsic | VIII, IX, XI, XII |
| Prolonged | Prolonged | Common | X, V, II, I |
| Normal | Normal | — | Factor XIII, platelets, vWD |

### Warfarin Monitoring
- Standard indication (DVT/PE/AFib): target INR 2.0–3.0
- Mechanical valve: target INR 2.5–3.5
- Dose adjustment recommendations based on INR

### Heparin Monitoring
- Unfractionated heparin: target aPTT 1.5–2.5× control
- Bolus and rate change recommendations
- LMWH: recommends anti-Xa monitoring

## Quick Start

```bash
# Interpret PT
python cli.py pt --pt 15.0

# Interpret INR with warfarin context
python cli.py inr --inr 2.5 --context warfarin_standard

# Mixing study
python cli.py mixing --patient-aptt 55 --immediate-mix 38 --control-aptt 30

# Factor deficiency pattern
python cli.py factors --pt 16 --aptt 50

# Warfarin dose assessment
python cli.py warfarin --inr 2.8 --indication standard

# Heparin therapy assessment
python cli.py heparin --aptt 55 --control-aptt 30

# Batch processing
python cli.py batch -i coag_tests.csv -o results.csv
```

### Python API

```python
from coag_sentinel import identify_factor_deficiency, assess_warfarin_dose

result = identify_factor_deficiency(pt_seconds=16.0, aptt_seconds=30.0)
print(result["pattern"])  # "PT prolonged, aPTT normal"
print(result["likely_deficiencies"])  # ["Factor VII"]

warfarin = assess_warfarin_dose(inr=2.5, indication="standard")
print(warfarin["status"])  # "In range"
```

## Running Tests

```bash
python -m pytest test_coag_sentinel.py -v
```

## License

MIT License.
