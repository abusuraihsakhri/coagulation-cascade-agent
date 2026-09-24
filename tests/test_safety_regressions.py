import csv

import pytest

from agents.base import AuditTrail
from coag_sentinel import (
    assess_heparin_therapy,
    interpret_mixing_study,
    interpret_pt,
    process_batch,
)


def test_audit_trail_detects_signature_tampering():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("tester", "unit", "CHECK", {"status": "ok"})
    assert trail.verify_integrity() is True

    trail.logs[0]["event_type"] = "TAMPERED"
    assert trail.verify_integrity() is False


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_pt_rejects_nonpositive_or_nonfinite_values(value):
    with pytest.raises(ValueError):
        interpret_pt(value)


def test_mixing_study_rejects_zero_patient_aptt():
    with pytest.raises(ValueError):
        interpret_mixing_study(0, 30, control_aptt=30)


def test_heparin_rejects_invalid_target_range():
    with pytest.raises(ValueError):
        assess_heparin_therapy(50, 30, therapeutic_ratio_range=(2.5, 1.5))


def test_batch_supports_documented_pt_and_mixing_modes(tmp_path):
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text(
        "mode,pt,patient_aptt,immediate_mix_aptt,control_aptt,ica_cutoff\n"
        "pt,12.0,,,,\n"
        "mixing_study,,55,32,30,15\n",
        encoding="utf-8",
    )

    assert process_batch(str(source), str(output)) == 2

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["status"] == "Normal"
    assert rows[1]["status"] == "Corrects at supplied cutoff"
