#!/usr/bin/env python3
"""
Coagulation Cascade Calculator & Interpreter.

Implements:
  - PT/INR interpretation (Normal PT 11-13.5s, INR 0.8-1.2)
  - aPTT interpretation (Normal 25-35 seconds)
  - Mixing study interpretation (immediate and 2-hour incubation)
  - Factor deficiency identification from PT/aPTT patterns
  - Warfarin monitoring (target INR 2-3, mechanical valve 2.5-3.5)
  - Heparin monitoring (target aPTT 1.5-2.5× control)

Zero-dependency Python stdlib implementation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import sys
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Reference Ranges
# ---------------------------------------------------------------------------

PT_NORMAL_RANGE = (11.0, 13.5)  # seconds
APTT_NORMAL_RANGE = (25.0, 35.0)  # seconds
INR_NORMAL_RANGE = (0.8, 1.2)


# ---------------------------------------------------------------------------
# PT/INR Interpretation
# ---------------------------------------------------------------------------

def interpret_pt(pt_seconds: float) -> Dict[str, Any]:
    """
    Interpret Prothrombin Time (PT).

    Args:
        pt_seconds: PT in seconds

    Returns:
        Dict with status, interpretation, and possible causes
    """
    low, high = PT_NORMAL_RANGE
    if low <= pt_seconds <= high:
        status = "Normal"
        interpretation = f"PT {pt_seconds:.1f}s is within normal range ({low}-{high}s)."
        causes = []
    elif pt_seconds < low:
        status = "Shortened"
        interpretation = f"PT {pt_seconds:.1f}s is below normal ({low}s). Shortened PT may indicate hypercoagulable state."
        causes = ["Hypercoagulable state", "Early DIC (hypercoagulable phase)", "Factor V Leiden (indirect)"]
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
        "normal_range": PT_NORMAL_RANGE,
        "status": status,
        "interpretation": interpretation,
        "possible_causes": causes,
    }


def interpret_inr(inr: float, therapeutic_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Interpret INR (International Normalized Ratio).

    Args:
        inr: INR value
        therapeutic_context: 'warfarin_standard', 'warfarin_mechanical_valve', or None

    Returns:
        Dict with status, interpretation, and therapeutic assessment
    """
    low, high = INR_NORMAL_RANGE

    result = {
        "test": "INR",
        "value": inr,
        "normal_range": INR_NORMAL_RANGE,
    }

    if low <= inr <= high:
        result["status"] = "Normal"
        result["interpretation"] = f"INR {inr:.2f} is within normal range ({low}-{high})."
    elif inr < low:
        result["status"] = "Below normal"
        result["interpretation"] = f"INR {inr:.2f} is below normal. May indicate hypercoagulable state."
    else:
        result["status"] = "Elevated"
        result["interpretation"] = f"INR {inr:.2f} is above normal ({high})."

    # Therapeutic assessment
    if therapeutic_context == "warfarin_standard":
        target_low, target_high = 2.0, 3.0
        result["therapeutic_target"] = f"INR {target_low}-{target_high} (standard warfarin)"
        if target_low <= inr <= target_high:
            result["therapeutic_status"] = "In therapeutic range"
            result["action"] = "Continue current warfarin dose."
        elif inr < target_low:
            result["therapeutic_status"] = "Below therapeutic range"
            result["action"] = "Consider increasing warfarin dose. Recheck INR in 1-2 weeks."
        elif inr <= 3.5:
            result["therapeutic_status"] = "Slightly above therapeutic range"
            result["action"] = "Consider reducing warfarin dose. Recheck INR in 1 week."
        elif inr <= 5.0:
            result["therapeutic_status"] = "Above therapeutic range (no significant bleeding)"
            result["action"] = "Hold warfarin 1-2 doses. Recheck INR. Consider vitamin K 1-2.5mg oral."
        else:
            result["therapeutic_status"] = "Critically elevated"
            result["action"] = "Hold warfarin. Give vitamin K 2.5-5mg oral. Recheck INR in 24h."

    elif therapeutic_context == "warfarin_mechanical_valve":
        target_low, target_high = 2.5, 3.5
        result["therapeutic_target"] = f"INR {target_low}-{target_high} (mechanical valve)"
        if target_low <= inr <= target_high:
            result["therapeutic_status"] = "In therapeutic range"
            result["action"] = "Continue current warfarin dose."
        elif inr < target_low:
            result["therapeutic_status"] = "Below therapeutic range"
            result["action"] = "Increase warfarin dose. High thrombotic risk with mechanical valve."
        elif inr <= 4.0:
            result["therapeutic_status"] = "Slightly above therapeutic range"
            result["action"] = "Reduce warfarin dose. Recheck INR in 3-5 days."
        else:
            result["therapeutic_status"] = "Significantly elevated"
            result["action"] = "Hold warfarin. Low-dose vitamin K. Close monitoring."

    return result


# ---------------------------------------------------------------------------
# aPTT Interpretation
# ---------------------------------------------------------------------------

def interpret_aptt(
    aptt_seconds: float,
    control_aptt: Optional[float] = None,
    heparin_monitoring: bool = False,
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
    low, high = APTT_NORMAL_RANGE
    result = {
        "test": "aPTT",
        "value": aptt_seconds,
        "unit": "seconds",
        "normal_range": APTT_NORMAL_RANGE,
    }

    if low <= aptt_seconds <= high:
        result["status"] = "Normal"
        result["interpretation"] = f"aPTT {aptt_seconds:.1f}s is within normal range ({low}-{high}s)."
        result["possible_causes"] = []
    elif aptt_seconds < low:
        result["status"] = "Shortened"
        result["interpretation"] = f"aPTT {aptt_seconds:.1f}s is below normal. May suggest hypercoagulable state."
        result["possible_causes"] = ["Hypercoagulable state", "Acute phase reaction (elevated Factor VIII)"]
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

    # Heparin monitoring
    if heparin_monitoring and control_aptt:
        ratio = aptt_seconds / control_aptt
        result["control_aptt"] = control_aptt
        result["aptt_ratio"] = round(ratio, 2)
        result["target_ratio_range"] = "1.5-2.5× control"

        if 1.5 <= ratio <= 2.5:
            result["therapeutic_status"] = "In therapeutic range"
            result["action"] = "Continue current heparin infusion rate."
        elif ratio < 1.5:
            result["therapeutic_status"] = "Below therapeutic range"
            result["action"] = "Increase heparin infusion rate. Recheck aPTT in 6 hours."
        elif ratio <= 3.0:
            result["therapeutic_status"] = "Above therapeutic range"
            result["action"] = "Decrease heparin infusion rate. Recheck aPTT in 6 hours."
        else:
            result["therapeutic_status"] = "Significantly supratherapeutic"
            result["action"] = "Stop heparin infusion. Recheck aPTT in 2-4 hours. Assess for bleeding."

    return result


# ---------------------------------------------------------------------------
# Mixing Study Interpretation
# ---------------------------------------------------------------------------

def interpret_mixing_study(
    patient_aptt: float,
    immediate_mix_aptt: float,
    incubated_mix_aptt: Optional[float] = None,
    control_aptt: float = 30.0,
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
    """
    rosner_index = abs(immediate_mix_aptt - control_aptt) / patient_aptt * 100
    correction_threshold = 10.0  # Rosner Index < 10% = correction

    result = {
        "patient_aptt": patient_aptt,
        "immediate_mix_aptt": immediate_mix_aptt,
        "control_aptt": control_aptt,
        "rosner_index": round(rosner_index, 2),
        "immediate_correction": rosner_index < correction_threshold,
    }

    if rosner_index < correction_threshold:
        result["immediate_interpretation"] = (
            "Mix corrects (Rosner Index {:.1f}% < 10%): suggests factor deficiency. "
            "Consider factor assays (VIII, IX, XI, XII)."
        ).format(rosner_index)
    else:
        result["immediate_interpretation"] = (
            "Mix does NOT correct (Rosner Index {:.1f}% ≥ 10%): suggests inhibitor. "
            "Consider lupus anticoagulant (dRVVT), specific factor inhibitor (e.g., Factor VIII inhibitor), "
            "or heparin contamination."
        ).format(rosner_index)

    # 2-hour incubation interpretation
    if incubated_mix_aptt is not None:
        result["incubated_mix_aptt"] = incubated_mix_aptt
        incubated_rosner = abs(incubated_mix_aptt - control_aptt) / patient_aptt * 100
        result["incubated_rosner_index"] = round(incubated_rosner, 2)

        if rosner_index < correction_threshold:
            # Immediate corrected
            if incubated_rosner >= correction_threshold:
                result["incubation_interpretation"] = (
                    "Immediate mix corrected but incubated mix prolongs: "
                    "suggests time-dependent factor inhibitor (e.g., Factor VIII inhibitor). "
                    "Order Bethesda titer."
                )
                result["diagnosis"] = "Factor inhibitor (time-dependent)"
            else:
                result["incubation_interpretation"] = (
                    "Both immediate and incubated mixes correct: "
                    "confirms factor deficiency. Order specific factor levels."
                )
                result["diagnosis"] = "Factor deficiency"
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
    pt_abnormal = pt_seconds > PT_NORMAL_RANGE[1]
    aptt_abnormal = aptt_seconds > APTT_NORMAL_RANGE[1]

    result = {
        "pt": pt_seconds,
        "aptt": aptt_seconds,
        "pt_prolonged": pt_abnormal,
        "aptt_prolonged": aptt_abnormal,
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
    Assess warfarin dosing based on INR.

    Args:
        inr: Current INR
        indication: 'standard' (DVT/PE/AFib) or 'mechanical_valve'
        previous_inr: Previous INR for trend analysis
        current_dose_mg: Current weekly dose in mg

    Returns:
        Dict with assessment and dose adjustment recommendation
    """
    if indication == "mechanical_valve":
        target = (2.5, 3.5)
    else:
        target = (2.0, 3.0)

    result = {
        "inr": inr,
        "indication": indication,
        "target_range": target,
        "current_dose_mg_per_week": current_dose_mg,
    }

    if target[0] <= inr <= target[1]:
        result["status"] = "In range"
        result["action"] = "Continue current dose."
        result["dose_adjustment"] = "None"
    elif inr < target[0]:
        deficit = target[0] - inr
        if deficit < 0.3:
            result["status"] = "Slightly below range"
            result["action"] = "Consider 5-10% dose increase. Recheck in 1-2 weeks."
            result["dose_adjustment"] = "Increase 5-10%"
        elif deficit < 0.5:
            result["status"] = "Below range"
            result["action"] = "Increase dose by 10-15%. Recheck in 1 week."
            result["dose_adjustment"] = "Increase 10-15%"
        else:
            result["status"] = "Significantly below range"
            result["action"] = "Increase dose by 15-20%. Consider bridging with LMWH if high thrombotic risk."
            result["dose_adjustment"] = "Increase 15-20%"
    else:
        excess = inr - target[1]
        if excess < 0.5:
            result["status"] = "Slightly above range"
            result["action"] = "Reduce dose by 5-15%. Recheck in 1 week."
            result["dose_adjustment"] = "Decrease 5-15%"
        elif excess < 1.0:
            result["status"] = "Above range"
            result["action"] = "Hold 1 dose, reduce weekly dose by 10-20%. Recheck in 3-5 days."
            result["dose_adjustment"] = "Hold 1 dose, decrease 10-20%"
        elif inr <= 5.0:
            result["status"] = "Significantly above range"
            result["action"] = "Hold warfarin. Give vitamin K 1-2.5mg orally. Recheck INR in 24h."
            result["dose_adjustment"] = "Hold, give vitamin K"
        elif inr <= 9.0:
            result["status"] = "Critically elevated"
            result["action"] = "Hold warfarin. Give vitamin K 2.5-5mg orally. Recheck INR in 24h. No active bleeding expected."
            result["dose_adjustment"] = "Hold, give vitamin K 2.5-5mg"
        else:
            result["status"] = "Dangerously elevated"
            result["action"] = "Hold warfarin. Give vitamin K 5-10mg IV slowly. Consider FFP/PCC if active bleeding or urgent surgery."
            result["dose_adjustment"] = "Hold, give vitamin K IV, consider FFP/PCC"

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
) -> Dict[str, Any]:
    """
    Assess heparin therapy based on aPTT.

    Args:
        aptt_seconds: Patient aPTT
        control_aptt: Control/normal aPTT
        heparin_type: 'unfractionated' or 'lmwh'

    Returns:
        Dict with therapeutic assessment
    """
    ratio = aptt_seconds / control_aptt

    result = {
        "aptt_seconds": aptt_seconds,
        "control_aptt": control_aptt,
        "ratio": round(ratio, 2),
        "heparin_type": heparin_type,
    }

    if heparin_type == "lmwh":
        result["note"] = "LMWH is typically monitored by anti-Xa levels, not aPTT."
        result["recommendation"] = "Order anti-Xa level for LMWH monitoring."
        return result

    # Unfractionated heparin
    result["target_ratio"] = "1.5-2.5× control"
    result["target_aptt_range"] = f"{control_aptt * 1.5:.1f}-{control_aptt * 2.5:.1f}s"

    if 1.5 <= ratio <= 2.5:
        result["status"] = "Therapeutic"
        result["action"] = "Continue current heparin infusion rate. Recheck aPTT in 6 hours."
        result["bolus"] = None
        result["rate_change"] = "No change"
    elif ratio < 1.5:
        result["status"] = "Subtherapeutic"
        if ratio < 1.2:
            result["action"] = "Give bolus 80 units/kg, increase infusion by 4 units/kg/hr. Recheck aPTT in 6 hours."
            result["bolus"] = "80 units/kg"
            result["rate_change"] = "Increase 4 units/kg/hr"
        else:
            result["action"] = "Increase infusion by 2 units/kg/hr. Recheck aPTT in 6 hours."
            result["bolus"] = None
            result["rate_change"] = "Increase 2 units/kg/hr"
    elif ratio <= 3.0:
        result["status"] = "Slightly supratherapeutic"
        result["action"] = "Decrease infusion by 2 units/kg/hr. Recheck aPTT in 6 hours."
        result["bolus"] = None
        result["rate_change"] = "Decrease 2 units/kg/hr"
    else:
        result["status"] = "Significantly supratherapeutic"
        result["action"] = "Stop heparin for 1 hour, decrease infusion by 3 units/kg/hr. Recheck aPTT in 4-6 hours. Assess for bleeding."
        result["bolus"] = None
        result["rate_change"] = "Stop 1hr, decrease 3 units/kg/hr"

    return result


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def process_batch(input_csv: str, output_csv: str) -> int:
    """
    Process a CSV of coagulation test results.

    Expected columns vary by mode:
      - interpret_pt: pt
      - interpret_aptt: aptt, control_aptt (optional)
      - mixing_study: patient_aptt, immediate_mix_aptt, incubated_mix_aptt (optional), control_aptt
      - factor_deficiency: pt, aptt, thrombin_time (optional)
      - warfarin: inr, indication (optional), previous_inr (optional)
      - heparin: aptt, control_aptt, heparin_type (optional)
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
            if mode == "factor_deficiency":
                pt = float(r.get("pt", 12))
                aptt = float(r.get("aptt", 30))
                tt = float(r["thrombin_time"]) if r.get("thrombin_time") else None
                result = identify_factor_deficiency(pt, aptt, tt)
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
                result = assess_heparin_therapy(aptt, control)
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
