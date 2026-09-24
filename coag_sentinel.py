#!/usr/bin/env python3
"""
Coagulation Cascade Calculator & Interpreter.

Implements:
  - PT/INR and aPTT reference-interval interpretation
  - Mixing-study ICA/Rosner calculations with a configurable cutoff
  - Factor-pattern interpretation from PT/aPTT
  - INR classification against explicit reference contexts
  - aPTT ratio calculation against an optional local UFH target range
  - CSV batch processing

The built-in PT/aPTT intervals are examples, not laboratory-universal limits.
Anticoagulant dose changes are deliberately not generated.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import sys
from typing import Dict, Any, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Reference Ranges
# ---------------------------------------------------------------------------

PT_NORMAL_RANGE = (11.0, 13.5)  # seconds
APTT_NORMAL_RANGE = (25.0, 35.0)  # seconds
INR_NORMAL_RANGE = (0.8, 1.2)


def _require_positive(value: float, name: str) -> float:
    """Return a finite positive float or raise ValueError."""
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value greater than 0")
    return value


def _validate_range(value: Tuple[float, float], name: str) -> Tuple[float, float]:
    low, high = map(float, value)
    if not math.isfinite(low) or not math.isfinite(high) or low <= 0 or high <= low:
        raise ValueError(f"{name} must contain finite positive values with low < high")
    return (low, high)


def _validate_ratio_range(value: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if value is None:
        return None
    return _validate_range(value, "therapeutic_ratio_range")


# ---------------------------------------------------------------------------
# PT/INR Interpretation
# ---------------------------------------------------------------------------

def interpret_pt(
    pt_seconds: float,
    reference_range: Tuple[float, float] = PT_NORMAL_RANGE,
) -> Dict[str, Any]:
    """
    Interpret Prothrombin Time (PT).

    Args:
        pt_seconds: PT in seconds

    Returns:
        Dict with status, interpretation, and possible causes
    """
    pt_seconds = _require_positive(pt_seconds, "pt_seconds")
    low, high = _validate_range(reference_range, "reference_range")
    if low <= pt_seconds <= high:
        status = "Normal"
        interpretation = f"PT {pt_seconds:.1f}s is within normal range ({low}-{high}s)."
        causes = []
    elif pt_seconds < low:
        status = "Shortened"
        interpretation = f"PT {pt_seconds:.1f}s is below the built-in example range ({low}s). A shortened PT is nonspecific."
        causes = [
            "Pre-analytic or reagent variation",
            "Higher factor VII activity / acute-phase variation",
            "Interpret with the local reference interval; PT alone is not a hypercoagulability test",
        ]
    else:
        status = "Prolonged"
        excess = pt_seconds - high
        if excess < 3:
            severity = "Mild"
        elif excess <= 6:
            severity = "Moderate"
        else:
            severity = "Severe"
        interpretation = f"PT {pt_seconds:.1f}s is prolonged ({severity}: {excess:.1f}s above upper normal)."
        causes = [
            "Warfarin/anticoagulant therapy",
            "Vitamin K deficiency",
            "Liver disease",
            "Factor VII deficiency",
            "DIC (consumption)",
            "Common pathway factor deficiency (X, V, II, I)",
        ]

    return {
        "test": "PT",
        "value": pt_seconds,
        "unit": "seconds",
        "normal_range": (low, high),
        "status": status,
        "interpretation": interpretation,
        "possible_causes": causes,
        "reference_note": "PT reference intervals are laboratory/reagent specific; the built-in range is an example.",
    }


def interpret_inr(
    inr: float,
    therapeutic_context: Optional[str] = None,
    reference_range: Tuple[float, float] = INR_NORMAL_RANGE,
) -> Dict[str, Any]:
    """
    Interpret INR (International Normalized Ratio).

    Args:
        inr: INR value
        therapeutic_context: 'warfarin_standard', 'warfarin_mechanical_valve', or None

    Returns:
        Dict with status, interpretation, and therapeutic assessment
    """
    inr = _require_positive(inr, "inr")
    low, high = _validate_range(reference_range, "reference_range")

    result = {
        "test": "INR",
        "value": inr,
        "normal_range": (low, high),
        "reference_note": "Interpret INR against the clinical indication and prescribed target; the non-anticoagulated range is contextual.",
    }

    if low <= inr <= high:
        result["status"] = "Normal"
        result["interpretation"] = f"INR {inr:.2f} is within normal range ({low}-{high})."
    elif inr < low:
        result["status"] = "Below normal"
        result["interpretation"] = f"INR {inr:.2f} is below the built-in example non-anticoagulated range; this finding is nonspecific."
    else:
        result["status"] = "Elevated"
        result["interpretation"] = f"INR {inr:.2f} is above normal ({high})."

    # Therapeutic-context classification. Treatment decisions are intentionally
    # not generated because INR targets and reversal/dose-adjustment protocols
    # depend on indication, valve type, bleeding status, interacting drugs, and
    # locally validated anticoagulation protocols.
    if therapeutic_context == "warfarin_standard":
        target_low, target_high = 2.0, 3.0
        result["therapeutic_target"] = f"INR {target_low}-{target_high} (common AF/VTE reference target)"
        if target_low <= inr <= target_high:
            result["therapeutic_status"] = "In therapeutic range"
        elif inr < target_low:
            result["therapeutic_status"] = "Below therapeutic range"
        elif inr <= 3.5:
            result["therapeutic_status"] = "Slightly above therapeutic range"
        elif inr <= 5.0:
            result["therapeutic_status"] = "Above therapeutic range"
        else:
            result["therapeutic_status"] = "Critically elevated"
        result["action"] = "Use the patient's prescribed INR target and the treating service's validated anticoagulation protocol; this tool does not recommend dose changes."

    elif therapeutic_context == "warfarin_mechanical_valve":
        result["therapeutic_target"] = "Valve- and risk-specific target required"
        result["therapeutic_status"] = "Context required"
        result["action"] = "Specify the mechanical valve position/type and thromboembolic risk factors; a single INR target is not appropriate for all mechanical valves."

    return result


# ---------------------------------------------------------------------------
# aPTT Interpretation
# ---------------------------------------------------------------------------

def interpret_aptt(
    aptt_seconds: float,
    control_aptt: Optional[float] = None,
    heparin_monitoring: bool = False,
    reference_range: Tuple[float, float] = APTT_NORMAL_RANGE,
) -> Dict[str, Any]:
    """
    Interpret Activated Partial Thromboplastin Time (aPTT).

    Args:
        aptt_seconds: Patient aPTT in seconds
        control_aptt: Control/normal aPTT for ratio calculation
        heparin_monitoring: Whether this is for heparin therapy monitoring

    Returns:
        Dict with status, interpretation, and therapeutic assessment
    """
    aptt_seconds = _require_positive(aptt_seconds, "aptt_seconds")
    if control_aptt is not None:
        control_aptt = _require_positive(control_aptt, "control_aptt")
    low, high = _validate_range(reference_range, "reference_range")
    result = {
        "test": "aPTT",
        "value": aptt_seconds,
        "unit": "seconds",
        "normal_range": (low, high),
        "reference_note": "aPTT reference intervals are laboratory/reagent specific; the built-in range is an example.",
    }

    if low <= aptt_seconds <= high:
        result["status"] = "Normal"
        result["interpretation"] = f"aPTT {aptt_seconds:.1f}s is within normal range ({low}-{high}s)."
        result["possible_causes"] = []
    elif aptt_seconds < low:
        result["status"] = "Shortened"
        result["interpretation"] = f"aPTT {aptt_seconds:.1f}s is below the built-in example range. A shortened aPTT is nonspecific."
        result["possible_causes"] = [
            "Pre-analytic or reagent variation",
            "Acute-phase elevation of factor VIII or other clotting factors",
            "Interpret with the local reference interval; aPTT alone is not a hypercoagulability test",
        ]
    else:
        result["status"] = "Prolonged"
        result["interpretation"] = f"aPTT {aptt_seconds:.1f}s is prolonged."
        result["possible_causes"] = [
            "Heparin therapy",
            "Factor VIII deficiency (Hemophilia A)",
            "Factor IX deficiency (Hemophilia B)",
            "Factor XI deficiency",
            "Factor XII deficiency",
            "von Willebrand disease",
            "Lupus anticoagulant",
            "Liver disease",
            "DIC",
            "Common pathway deficiency (X, V, II, I)",
        ]

    # aPTT response to UFH is reagent/coagulometer dependent. Report the ratio
    # without applying a universal therapeutic target.
    if heparin_monitoring:
        if control_aptt is None:
            raise ValueError("control_aptt is required when heparin_monitoring=True")
        ratio = aptt_seconds / control_aptt
        result["control_aptt"] = control_aptt
        result["aptt_ratio"] = round(ratio, 2)
        result["target_ratio_range"] = "Institution/reagent-specific"
        result["therapeutic_status"] = "Target range required"
        result["action"] = "Apply the local UFH aPTT therapeutic range or an anti-Xa-based protocol; no infusion change is generated by this tool."

    return result


# ---------------------------------------------------------------------------
# Mixing Study Interpretation
# ---------------------------------------------------------------------------

def interpret_mixing_study(
    patient_aptt: float,
    immediate_mix_aptt: float,
    incubated_mix_aptt: Optional[float] = None,
    control_aptt: float = 30.0,
    ica_cutoff: float = 15.0,
) -> Dict[str, Any]:
    """
    Interpret aPTT mixing study.

    A mixing study mixes patient plasma 1:1 with normal pooled plasma.

    Immediate mix:
      - If corrects (within normal or within 10% of control): factor deficiency likely
      - If does not correct: inhibitor likely (lupus anticoagulant, specific factor inhibitor)

    2-hour incubation:
      - If prolongs after incubation: factor inhibitor (e.g., Factor VIII inhibitor)
      - If stays corrected: factor deficiency confirmed
      - LA typically does not correct on immediate mix

    Rosner/ICA = |aPTT mix - aPTT control| / aPTT patient × 100.
    The cutoff is assay/laboratory specific and can be supplied by the caller.

    Args:
        patient_aptt: Patient's aPTT (seconds)
        immediate_mix_aptt: aPTT of 1:1 immediate mix (seconds)
        incubated_mix_aptt: aPTT of 1:1 mix after 2-hour incubation (seconds)
        control_aptt: Normal pooled plasma aPTT (seconds)

    Returns:
        Dict with mixing study interpretation
    """
    patient_aptt = _require_positive(patient_aptt, "patient_aptt")
    immediate_mix_aptt = _require_positive(immediate_mix_aptt, "immediate_mix_aptt")
    control_aptt = _require_positive(control_aptt, "control_aptt")
    if incubated_mix_aptt is not None:
        incubated_mix_aptt = _require_positive(incubated_mix_aptt, "incubated_mix_aptt")
    correction_threshold = _require_positive(ica_cutoff, "ica_cutoff")
    rosner_index = abs(immediate_mix_aptt - control_aptt) / patient_aptt * 100

    result = {
        "patient_aptt": patient_aptt,
        "immediate_mix_aptt": immediate_mix_aptt,
        "control_aptt": control_aptt,
        "rosner_index": round(rosner_index, 2),
        "ica_cutoff": correction_threshold,
        "cutoff_note": "Use a locally validated assay-specific cutoff where available.",
        "immediate_correction": rosner_index <= correction_threshold,
    }

    if rosner_index <= correction_threshold:
        result["immediate_interpretation"] = (
            "Mix meets the supplied ICA correction cutoff "
            f"({rosner_index:.1f}% <= {correction_threshold:.1f}%): factor deficiency is favored, "
            "subject to local assay validation and the clinical context."
        )
    else:
        result["immediate_interpretation"] = (
            "Mix exceeds the supplied ICA correction cutoff "
            f"({rosner_index:.1f}% > {correction_threshold:.1f}%): an inhibitor is favored. "
            "Interpret with assay-specific cutoffs and appropriate confirmatory testing."
        )

    # 2-hour incubation interpretation
    if incubated_mix_aptt is not None:
        result["incubated_mix_aptt"] = incubated_mix_aptt
        incubated_rosner = abs(incubated_mix_aptt - control_aptt) / patient_aptt * 100
        result["incubated_rosner_index"] = round(incubated_rosner, 2)

        if rosner_index <= correction_threshold:
            # Immediate corrected
            if incubated_rosner > correction_threshold:
                result["incubation_interpretation"] = (
                    "Immediate mix corrected but incubated mix prolongs: "
                    "suggests time-dependent factor inhibitor (e.g., Factor VIII inhibitor). "
                    "Order Bethesda titer."
                )
                result["diagnosis"] = "Factor inhibitor (time-dependent)"
            else:
                result["incubation_interpretation"] = (
                    "Both immediate and incubated mixes meet the supplied correction cutoff: "
                    "supports a factor-deficiency pattern; correlate with specific factor assays."
                )
                result["diagnosis"] = "Factor deficiency pattern"
        else:
            # Immediate did not correct
            if incubated_rosner > rosner_index:
                result["incubation_interpretation"] = (
                    "Immediate mix did not correct, and incubated mix further prolongs: "
                    "strongly suggests factor inhibitor (time-dependent)."
                )
                result["diagnosis"] = "Factor inhibitor (strong)"
            else:
                result["incubation_interpretation"] = (
                    "Immediate mix did not correct: "
                    "suggests immediate-acting inhibitor (lupus anticoagulant, heparin)."
                )
                result["diagnosis"] = "Immediate-acting inhibitor (LA or heparin)"

    return result


# ---------------------------------------------------------------------------
# Factor Deficiency Pattern Recognition
# ---------------------------------------------------------------------------

def identify_factor_deficiency(
    pt_seconds: float,
    aptt_seconds: float,
    thrombin_time: Optional[float] = None,
    pt_upper: float = PT_NORMAL_RANGE[1],
    aptt_upper: float = APTT_NORMAL_RANGE[1],
) -> Dict[str, Any]:
    """
    Identify likely factor deficiency from PT/aPTT pattern.

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
    """
    pt_seconds = _require_positive(pt_seconds, "pt_seconds")
    aptt_seconds = _require_positive(aptt_seconds, "aptt_seconds")
    if thrombin_time is not None:
        thrombin_time = _require_positive(thrombin_time, "thrombin_time")
    pt_upper = _require_positive(pt_upper, "pt_upper")
    aptt_upper = _require_positive(aptt_upper, "aptt_upper")
    pt_abnormal = pt_seconds > pt_upper
    aptt_abnormal = aptt_seconds > aptt_upper

    result = {
        "pt": pt_seconds,
        "aptt": aptt_seconds,
        "pt_prolonged": pt_abnormal,
        "aptt_prolonged": aptt_abnormal,
        "pt_upper_limit": pt_upper,
        "aptt_upper_limit": aptt_upper,
    }

    if pt_abnormal and not aptt_abnormal:
        result["pattern"] = "PT prolonged, aPTT normal"
        result["pathway"] = "Extrinsic pathway"
        result["likely_deficiencies"] = ["Factor VII"]
        result["differential"] = [
            "Factor VII deficiency (congenital or acquired)",
            "Early vitamin K deficiency",
            "Early warfarin effect",
            "Early liver disease",
        ]
        result["recommended_workup"] = [
            "Factor VII level",
            "Vitamin K level",
            "Liver function tests",
        ]

    elif not pt_abnormal and aptt_abnormal:
        result["pattern"] = "PT normal, aPTT prolonged"
        result["pathway"] = "Intrinsic pathway"
        result["likely_deficiencies"] = ["Factor VIII", "Factor IX", "Factor XI", "Factor XII"]
        result["differential"] = [
            "Hemophilia A (Factor VIII deficiency)",
            "Hemophilia B (Factor IX deficiency)",
            "Factor XI deficiency",
            "Factor XII deficiency (usually incidental, not clinically significant)",
            "von Willebrand disease (if Factor VIII low secondary to low vWF)",
            "Lupus anticoagulant (aPTT prolonged but no bleeding risk)",
            "Heparin contamination",
        ]
        result["recommended_workup"] = [
            "Factor VIII, IX, XI, XII levels",
            "von Willebrand panel (antigen, activity, multimers)",
            "Lupus anticoagulant (dRVVT, SCT)",
            "Mixing study",
        ]

    elif pt_abnormal and aptt_abnormal:
        result["pattern"] = "Both PT and aPTT prolonged"
        result["pathway"] = "Common pathway or multiple factor deficiency"
        result["likely_deficiencies"] = ["Factor X", "Factor V", "Factor II (prothrombin)", "Factor I (fibrinogen)"]
        result["differential"] = [
            "Liver disease (decreased synthesis of all factors)",
            "DIC (consumption of factors and platelets)",
            "Vitamin K deficiency (severe)",
            "Warfarin overdose",
            "Common pathway factor deficiency (X, V, II, I)",
            "Massive transfusion (dilutional coagulopathy)",
            "Direct oral anticoagulant (DOAC) effect",
        ]
        result["recommended_workup"] = [
            "Factor X, V, II, I levels",
            "Fibrinogen level",
            "D-dimer, FDP",
            "Liver function tests",
            "DIC panel (platelets, D-dimer, fibrinogen, PT)",
            "Mixing study",
        ]

    else:
        result["pattern"] = "Both PT and aPTT normal"
        result["pathway"] = "No intrinsic/extrinsic/common pathway deficiency detected"
        result["likely_deficiencies"] = []
        result["differential"] = [
            "Factor XIII deficiency (normal PT/aPTT — order Factor XIII assay)",
            "Platelet function disorder",
            "von Willebrand disease (mild — may have normal aPTT)",
            "Vascular disorder",
            "Medication effect (aspirin, NSAIDs — affect platelets, not PT/aPTT)",
        ]
        result["recommended_workup"] = [
            "Factor XIII assay (qualitative urea clot solubility test)",
            "Platelet function analyzer (PFA-100)",
            "von Willebrand panel",
            "Platelet aggregation studies",
        ]

    # Thrombin time interpretation
    if thrombin_time is not None:
        result["thrombin_time"] = thrombin_time
        tt_normal = (14.0, 19.0)
        if thrombin_time > tt_normal[1]:
            result["tt_prolonged"] = True
            result["tt_interpretation"] = (
                "Thrombin time prolonged: suggests fibrinogen abnormality "
                "(hypofibrinogenemia, dysfibrinogenemia) or heparin effect."
            )
        else:
            result["tt_prolonged"] = False
            result["tt_interpretation"] = "Thrombin time normal: fibrinogen conversion intact."

    return result


# ---------------------------------------------------------------------------
# Warfarin Monitoring
# ---------------------------------------------------------------------------

def assess_warfarin_dose(
    inr: float,
    indication: str = "standard",
    previous_inr: Optional[float] = None,
    current_dose_mg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Classify INR relative to a reference target without issuing a dose change.

    The legacy "mechanical_valve" context is retained for compatibility but
    intentionally requires more context because target INR depends on valve
    position/type and thromboembolic risk factors.
    """
    inr = _require_positive(inr, "inr")
    if previous_inr is not None:
        previous_inr = _require_positive(previous_inr, "previous_inr")
    if current_dose_mg is not None:
        current_dose_mg = _require_positive(current_dose_mg, "current_dose_mg")

    normalized = str(indication).strip().lower()
    targets = {
        "standard": ((2.0, 3.0), "Common AF/VTE reference target; confirm the prescribed patient-specific target."),
        "mechanical_mitral": ((2.5, 3.5), "Reference range centered on INR 3.0; confirm current valve guideline and patient factors."),
        "mechanical_aortic_bileaflet_no_risk": ((2.0, 3.0), "Reference range centered on INR 2.5 for selected current-generation AVR without risk factors."),
        "mechanical_aortic_high_risk": ((2.5, 3.5), "Reference range centered on INR 3.0 when higher-risk mechanical AVR context applies."),
    }

    result: Dict[str, Any] = {
        "inr": inr,
        "indication": normalized,
        "current_dose_mg_per_week": current_dose_mg,
        "dose_adjustment": "Not provided",
        "action": "Use the treating service's validated anticoagulation protocol; this tool does not recommend warfarin dose changes or reversal treatment.",
    }

    if normalized == "mechanical_valve":
        result["target_range"] = None
        result["status"] = "Target context required"
        result["target_note"] = "Specify valve position/type and thromboembolic risk factors; no single INR range covers all mechanical valves."
    elif normalized not in targets:
        result["target_range"] = None
        result["status"] = "Target context required"
        result["target_note"] = "Unknown indication. Supply a supported context or interpret against the patient's prescribed target."
    else:
        target, note = targets[normalized]
        result["target_range"] = target
        result["target_note"] = note
        if target[0] <= inr <= target[1]:
            result["status"] = "In range"
        elif inr < target[0]:
            deficit = target[0] - inr
            if deficit < 0.3:
                result["status"] = "Slightly below range"
            elif deficit < 0.5:
                result["status"] = "Below range"
            else:
                result["status"] = "Significantly below range"
        else:
            excess = inr - target[1]
            if excess < 0.5:
                result["status"] = "Slightly above range"
            elif excess < 1.0:
                result["status"] = "Above range"
            elif inr <= 5.0:
                result["status"] = "Significantly above range"
            elif inr <= 9.0:
                result["status"] = "Critically elevated"
            else:
                result["status"] = "Dangerously elevated"

    if previous_inr is not None:
        result["previous_inr"] = previous_inr
        trend = inr - previous_inr
        result["inr_trend"] = round(trend, 2)
        if abs(trend) > 0.5:
            result["trend_alert"] = "Significant INR change (>0.5) since last check."

    return result


# ---------------------------------------------------------------------------
# Heparin Monitoring
# ---------------------------------------------------------------------------

def assess_heparin_therapy(
    aptt_seconds: float,
    control_aptt: float,
    heparin_type: str = "unfractionated",
    therapeutic_ratio_range: Optional[Tuple[float, float]] = None,
) -> Dict[str, Any]:
    """
    Report aPTT ratio and optionally classify it against a supplied local range.

    A universal 1.5-2.5x aPTT target and a generic infusion nomogram are not
    applied because aPTT responsiveness varies by reagent/coagulometer and
    treatment protocols are institution-specific.
    """
    aptt_seconds = _require_positive(aptt_seconds, "aptt_seconds")
    control_aptt = _require_positive(control_aptt, "control_aptt")
    target = _validate_ratio_range(therapeutic_ratio_range)
    ratio = aptt_seconds / control_aptt
    heparin_type = str(heparin_type).strip().lower()

    result: Dict[str, Any] = {
        "aptt_seconds": aptt_seconds,
        "control_aptt": control_aptt,
        "ratio": round(ratio, 2),
        "heparin_type": heparin_type,
        "action": "No automated infusion change is generated. Apply the institution's validated UFH/anti-Xa protocol.",
    }

    if heparin_type == "lmwh":
        result["status"] = "aPTT not appropriate for routine LMWH monitoring"
        result["note"] = "LMWH is generally not titrated by aPTT; use the clinically indicated assay and local protocol."
        result["therapeutic_ratio_range"] = None
        return result

    if target is None:
        result["status"] = "Target range required"
        result["therapeutic_ratio_range"] = None
        result["note"] = "Provide a locally validated aPTT ratio range if ratio-based classification is desired."
        return result

    low, high = target
    result["therapeutic_ratio_range"] = target
    if ratio < low:
        result["status"] = "Below supplied range"
    elif ratio > high:
        result["status"] = "Above supplied range"
    else:
        result["status"] = "Within supplied range"
    return result


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def process_batch(input_csv: str, output_csv: str) -> int:
    """
    Process a CSV of coagulation test results.

    Expected columns vary by mode:
      - interpret_pt: pt, pt_reference_low/high (optional)
      - interpret_aptt: aptt, aptt_reference_low/high (optional)
      - mixing_study: patient_aptt, immediate_mix_aptt, incubated_mix_aptt (optional), control_aptt
      - factor_deficiency: pt, aptt, thrombin_time (optional)
      - warfarin: inr, indication (optional), previous_inr (optional)
      - heparin: aptt, control_aptt, heparin_type (optional), target_ratio_low/high (optional)
    """
    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    out_fields = fieldnames + ["interpretation", "status", "action"]
    out_rows = []

    for r in rows:
        mode = r.get("mode", "factor_deficiency").strip().lower()
        row_dict = dict(r)

        try:
            if mode in {"interpret_pt", "pt"}:
                pt = float(r.get("pt", ""))
                pt_range = (
                    float(r.get("pt_reference_low", PT_NORMAL_RANGE[0])),
                    float(r.get("pt_reference_high", PT_NORMAL_RANGE[1])),
                )
                result = interpret_pt(pt, pt_range)
                row_dict["interpretation"] = result["interpretation"]
                row_dict["status"] = result["status"]
                row_dict["action"] = "Use the local laboratory reference interval for final interpretation."

            elif mode in {"interpret_aptt", "aptt"}:
                aptt = float(r.get("aptt", ""))
                control = float(r["control_aptt"]) if r.get("control_aptt") else None
                aptt_range = (
                    float(r.get("aptt_reference_low", APTT_NORMAL_RANGE[0])),
                    float(r.get("aptt_reference_high", APTT_NORMAL_RANGE[1])),
                )
                result = interpret_aptt(
                    aptt,
                    control_aptt=control,
                    heparin_monitoring=False,
                    reference_range=aptt_range,
                )
                row_dict["interpretation"] = result["interpretation"]
                row_dict["status"] = result["status"]
                row_dict["action"] = "Use the local laboratory reference interval for final interpretation."

            elif mode in {"mixing_study", "mixing"}:
                patient = float(r.get("patient_aptt", r.get("aptt", "")))
                immediate = float(r.get("immediate_mix_aptt", ""))
                incubated = float(r["incubated_mix_aptt"]) if r.get("incubated_mix_aptt") else None
                control = float(r.get("control_aptt", 30.0))
                cutoff = float(r.get("ica_cutoff", 15.0))
                result = interpret_mixing_study(patient, immediate, incubated, control, cutoff)
                row_dict["interpretation"] = result["immediate_interpretation"]
                row_dict["status"] = "Corrects at supplied cutoff" if result["immediate_correction"] else "Does not correct at supplied cutoff"
                row_dict["action"] = "Confirm the cutoff and interpretation against the local assay validation."

            elif mode == "factor_deficiency":
                pt = float(r.get("pt", 12))
                aptt = float(r.get("aptt", 30))
                tt = float(r["thrombin_time"]) if r.get("thrombin_time") else None
                pt_upper = float(r.get("pt_reference_high", PT_NORMAL_RANGE[1]))
                aptt_upper = float(r.get("aptt_reference_high", APTT_NORMAL_RANGE[1]))
                result = identify_factor_deficiency(pt, aptt, tt, pt_upper, aptt_upper)
                row_dict["interpretation"] = result["pattern"]
                row_dict["status"] = result["pathway"]
                row_dict["action"] = ", ".join(result["recommended_workup"])

            elif mode == "warfarin":
                inr = float(r.get("inr", 1.0))
                indication = r.get("indication", "standard")
                result = assess_warfarin_dose(inr, indication)
                row_dict["interpretation"] = f"INR {inr} - {result['status']}"
                row_dict["status"] = result["status"]
                row_dict["action"] = result["action"]

            elif mode == "heparin":
                aptt = float(r.get("aptt", 30))
                control = float(r.get("control_aptt", 30))
                low = float(r["target_ratio_low"]) if r.get("target_ratio_low") else None
                high = float(r["target_ratio_high"]) if r.get("target_ratio_high") else None
                target = (low, high) if low is not None and high is not None else None
                result = assess_heparin_therapy(aptt, control, r.get("heparin_type", "unfractionated"), target)
                row_dict["interpretation"] = f"aPTT ratio {result['ratio']} - {result['status']}"
                row_dict["status"] = result["status"]
                row_dict["action"] = result["action"]

            else:
                row_dict["interpretation"] = f"Unknown mode: {mode}"
                row_dict["status"] = "ERROR"
                row_dict["action"] = ""

        except (ValueError, KeyError) as e:
            row_dict["interpretation"] = f"ERROR: {e}"
            row_dict["status"] = "ERROR"
            row_dict["action"] = ""

        out_rows.append(row_dict)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
