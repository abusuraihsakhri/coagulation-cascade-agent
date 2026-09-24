# Coagulation Cascade Agent

### [Open the Live Application →](https://abusuraihsakhri.github.io/coagulation-cascade-agent/)

Python and browser-based utilities for coagulation laboratory calculations and pattern interpretation. The repository includes PT/aPTT reference-interval checks, PT/aPTT pathway-pattern classification, mixing-study ICA/Rosner calculations, INR target-context classification, aPTT ratio calculations, and CSV batch processing.

> **Clinical limitation:** this project is a laboratory/research utility. Reference intervals, mixing-study cutoffs, anticoagulation targets, and escalation procedures must be validated for the local laboratory and clinical protocol. The software does not prescribe warfarin doses, heparin infusion changes, or reversal treatment.

## Features

- PT and aPTT interpretation with caller-supplied reference ranges.
- PT/aPTT pattern mapping for extrinsic, intrinsic, common-pathway, and non-prolonged patterns.
- Mixing-study ICA/Rosner calculation with a configurable laboratory cutoff and optional incubated result.
- INR classification against explicit reference contexts without automated dose adjustment.
- UFH aPTT ratio calculation with optional locally validated therapeutic bounds.
- CSV batch processing for PT, aPTT, mixing studies, factor-pattern assessment, INR classification, and heparin-ratio assessment.
- Responsive client-side web interface with light mode by default and an optional dark theme.
- Pytest coverage, package-build checks, installed CLI smoke tests, dependency auditing, and GitHub Pages deployment.

## Web interface

The static application is in `web/`. It performs its calculations in the browser with plain JavaScript and makes no network requests. No form data are uploaded or stored by the application; only the selected theme is saved in local browser storage.

The browser interface intentionally does not load Pyodide. The current calculations are small arithmetic/rule operations and do not require Python-only libraries, so a Python WebAssembly runtime would add substantial startup cost without improving the workflow.

## Installation

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

For development and testing:

```bash
python -m pip install -e ".[dev]"
```

The optional compatibility API requires:

```bash
python -m pip install -e ".[server]"
```

## CLI examples

### PT with a laboratory-specific reference interval

```bash
coag-cascade pt --pt 12.8 --reference-low 10.5 --reference-high 13.0
```

### aPTT

```bash
coag-cascade aptt --aptt 38 --reference-low 24 --reference-high 34
```

### Mixing study

```bash
coag-cascade mixing \
  --patient-aptt 55 \
  --immediate-mix 32 \
  --incubated-mix 48 \
  --control-aptt 30 \
  --ica-cutoff 15
```

The ICA/Rosner cutoff is configurable because correction criteria are assay- and laboratory-specific.

### PT/aPTT factor-pattern assessment

```bash
coag-cascade factors \
  --pt 16 \
  --aptt 30 \
  --pt-upper 13.5 \
  --aptt-upper 35
```

### INR target-context classification

```bash
coag-cascade warfarin --inr 2.8 --indication standard
```

Supported mechanical-valve reference contexts are `mechanical_mitral`, `mechanical_aortic_bileaflet_no_risk`, and `mechanical_aortic_high_risk`. The legacy `mechanical_valve` value is accepted but intentionally returns that more valve/risk context is required.

### UFH aPTT ratio with a locally validated range

```bash
coag-cascade heparin \
  --aptt 52.5 \
  --control-aptt 30 \
  --target-ratio-low 1.5 \
  --target-ratio-high 2.5
```

The supplied range is used only for classification. The tool does not generate an infusion-rate change.

### Batch processing

```bash
coag-cascade batch -i sample.csv -o results.csv
```

Supported `mode` values include `pt`, `aptt`, `mixing_study`, `factor_deficiency`, `warfarin`, and `heparin`. Optional CSV columns can provide local reference limits, an ICA cutoff, or UFH ratio bounds.

## Reference-range behavior

The module retains example defaults for backward compatibility:

- PT: 11.0–13.5 s
- aPTT: 25.0–35.0 s
- non-anticoagulated INR: 0.8–1.2

These values are not universal. PT/aPTT reference intervals depend on the assay, reagent, instrument, and laboratory validation. For clinical use, pass the laboratory's own limits.

Likewise, aPTT response to unfractionated heparin is reagent/coagulometer dependent, and mechanical-valve INR targets depend on valve position/type and thromboembolic risk factors. The anticoagulation helpers therefore classify values but do not prescribe treatment changes.

## Compatibility modules

The `agents/` and `coagulation_cascade_agent/` namespaces retain older demonstration APIs for compatibility. Their generic thresholds are explicitly nonclinical and are not presented as CAP, CLSI, ISO, ISTH, or other guideline-derived decision rules. The deterministic mock adapter does not silently connect to external model providers.

The identifier-pattern screen in `agents/base.py` is a defensive programming aid only. It is not a HIPAA Safe Harbor implementation and does not certify de-identification.

## Testing

```bash
python -m pytest -p no:zarr -q
python -m build
```

CI runs the test suite and package build on Python 3.10, 3.11, and 3.12, exercises both installed console-script names, smoke-tests the static site, and runs a dependency audit.

## Local web preview

```bash
python -m http.server 8000 --directory web
```

Then open `http://127.0.0.1:8000/`.

## Technology and browser support

- Python 3.10+
- Pydantic 2.x for compatibility schemas
- Vanilla HTML, CSS, and JavaScript for the browser interface
- Optional FastAPI/Uvicorn compatibility server
- Current versions of Chromium, Firefox, and Safari

## License

MIT. See [LICENSE](LICENSE).
