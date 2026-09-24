#!/usr/bin/env python3
"""Tests for Coagulation Cascade Calculator & Interpreter."""
import json
import os
import tempfile
import unittest

from coag_sentinel import (
    interpret_pt,
    interpret_inr,
    interpret_aptt,
    interpret_mixing_study,
    identify_factor_deficiency,
    assess_warfarin_dose,
    assess_heparin_therapy,
    process_batch,
    PT_NORMAL_RANGE,
    APTT_NORMAL_RANGE,
    INR_NORMAL_RANGE,
)


class TestInterpretPT(unittest.TestCase):
    def test_normal_pt(self):
        result = interpret_pt(12.0)
        self.assertEqual(result["status"], "Normal")

    def test_prolonged_pt_mild(self):
        result = interpret_pt(15.0)
        self.assertEqual(result["status"], "Prolonged")

    def test_prolonged_pt_severe(self):
        result = interpret_pt(25.0)
        self.assertEqual(result["status"], "Prolonged")
        self.assertTrue(any("Severe" in result["interpretation"] for _ in [1]))

    def test_shortened_pt(self):
        result = interpret_pt(9.0)
        self.assertEqual(result["status"], "Shortened")

    def test_pt_boundary_low(self):
        result = interpret_pt(11.0)
        self.assertEqual(result["status"], "Normal")

    def test_pt_boundary_high(self):
        result = interpret_pt(13.5)
        self.assertEqual(result["status"], "Normal")


class TestInterpretINR(unittest.TestCase):
    def test_normal_inr(self):
        result = interpret_inr(1.0)
        self.assertEqual(result["status"], "Normal")

    def test_elevated_inr(self):
        result = interpret_inr(3.0)
        self.assertEqual(result["status"], "Elevated")

    def test_warfarin_standard_in_range(self):
        result = interpret_inr(2.5, "warfarin_standard")
        self.assertEqual(result["therapeutic_status"], "In therapeutic range")

    def test_warfarin_standard_below(self):
        result = interpret_inr(1.5, "warfarin_standard")
        self.assertEqual(result["therapeutic_status"], "Below therapeutic range")

    def test_warfarin_standard_above(self):
        result = interpret_inr(3.5, "warfarin_standard")
        self.assertEqual(result["therapeutic_status"], "Slightly above therapeutic range")

    def test_warfarin_mechanical_valve_requires_context(self):
        result = interpret_inr(3.0, "warfarin_mechanical_valve")
        self.assertEqual(result["therapeutic_status"], "Context required")

    def test_warfarin_critically_elevated(self):
        result = interpret_inr(6.0, "warfarin_standard")
        self.assertEqual(result["therapeutic_status"], "Critically elevated")


class TestInterpretAPTT(unittest.TestCase):
    def test_normal_aptt(self):
        result = interpret_aptt(30.0)
        self.assertEqual(result["status"], "Normal")

    def test_prolonged_aptt(self):
        result = interpret_aptt(50.0)
        self.assertEqual(result["status"], "Prolonged")

    def test_shortened_aptt(self):
        result = interpret_aptt(20.0)
        self.assertEqual(result["status"], "Shortened")

    def test_heparin_monitoring_reports_ratio_without_universal_target(self):
        result = interpret_aptt(52.5, control_aptt=30.0, heparin_monitoring=True)
        self.assertEqual(result["therapeutic_status"], "Target range required")
        self.assertEqual(result["aptt_ratio"], 1.75)

    def test_heparin_monitoring_requires_control(self):
        with self.assertRaises(ValueError):
            interpret_aptt(35.0, heparin_monitoring=True)


class TestMixingStudy(unittest.TestCase):
    def test_factor_deficiency_correction(self):
        """Mix corrects → factor deficiency."""
        result = interpret_mixing_study(
            patient_aptt=55.0,
            immediate_mix_aptt=32.0,
            control_aptt=30.0,
        )
        self.assertTrue(result["immediate_correction"])
        self.assertIn("factor deficiency", result["immediate_interpretation"].lower())

    def test_inhibitor_no_correction(self):
        """Mix does NOT correct → inhibitor."""
        result = interpret_mixing_study(
            patient_aptt=55.0,
            immediate_mix_aptt=48.0,
            control_aptt=30.0,
        )
        self.assertFalse(result["immediate_correction"])
        self.assertIn("inhibitor", result["immediate_interpretation"].lower())

    def test_factor_inhibitor_with_incubation(self):
        """Immediate corrects but incubated prolongs → factor inhibitor."""
        result = interpret_mixing_study(
            patient_aptt=55.0,
            immediate_mix_aptt=32.0,
            incubated_mix_aptt=48.0,
            control_aptt=30.0,
        )
        self.assertTrue(result["immediate_correction"])
        self.assertIn("time-dependent", result.get("diagnosis", "").lower())

    def test_factor_deficiency_with_incubation(self):
        """Both correct → confirmed factor deficiency."""
        result = interpret_mixing_study(
            patient_aptt=55.0,
            immediate_mix_aptt=32.0,
            incubated_mix_aptt=33.0,
            control_aptt=30.0,
        )
        self.assertEqual(result.get("diagnosis"), "Factor deficiency pattern")


class TestFactorDeficiency(unittest.TestCase):
    def test_factor_vii_pattern(self):
        """PT prolonged, aPTT normal → Factor VII."""
        result = identify_factor_deficiency(16.0, 30.0)
        self.assertEqual(result["pattern"], "PT prolonged, aPTT normal")
        self.assertIn("Factor VII", result["likely_deficiencies"])

    def test_intrinsic_pattern(self):
        """PT normal, aPTT prolonged → VIII, IX, XI, XII."""
        result = identify_factor_deficiency(12.0, 50.0)
        self.assertEqual(result["pattern"], "PT normal, aPTT prolonged")
        self.assertIn("Factor VIII", result["likely_deficiencies"])
        self.assertIn("Factor IX", result["likely_deficiencies"])

    def test_common_pathway_pattern(self):
        """Both prolonged → common pathway."""
        result = identify_factor_deficiency(18.0, 50.0)
        self.assertEqual(result["pattern"], "Both PT and aPTT prolonged")
        self.assertIn("Factor X", result["likely_deficiencies"])

    def test_both_normal(self):
        """Both normal → consider Factor XIII."""
        result = identify_factor_deficiency(12.0, 30.0)
        self.assertEqual(result["pattern"], "Both PT and aPTT normal")
        self.assertIn("Factor XIII", str(result["differential"]))

    def test_thrombin_time_prolonged(self):
        """Prolonged TT suggests fibrinogen issue."""
        result = identify_factor_deficiency(18.0, 50.0, thrombin_time=25.0)
        self.assertTrue(result["tt_prolonged"])


class TestWarfarinDose(unittest.TestCase):
    def test_in_range(self):
        result = assess_warfarin_dose(2.5, "standard")
        self.assertEqual(result["status"], "In range")

    def test_below_range(self):
        result = assess_warfarin_dose(1.5, "standard")
        self.assertEqual(result["status"], "Significantly below range")

    def test_above_range(self):
        result = assess_warfarin_dose(3.8, "standard")
        self.assertEqual(result["status"], "Above range")

    def test_mechanical_valve_requires_specific_context(self):
        result = assess_warfarin_dose(3.0, "mechanical_valve")
        self.assertEqual(result["status"], "Target context required")

    def test_mechanical_mitral_reference_context(self):
        result = assess_warfarin_dose(3.0, "mechanical_mitral")
        self.assertEqual(result["status"], "In range")

    def test_dangerously_elevated(self):
        result = assess_warfarin_dose(10.0, "standard")
        self.assertEqual(result["status"], "Dangerously elevated")

    def test_with_previous_inr(self):
        result = assess_warfarin_dose(3.0, "standard", previous_inr=2.0)
        self.assertIn("inr_trend", result)


class TestHeparinTherapy(unittest.TestCase):
    def test_target_range_required_by_default(self):
        result = assess_heparin_therapy(52.5, 30.0)
        self.assertEqual(result["status"], "Target range required")

    def test_within_supplied_local_range(self):
        result = assess_heparin_therapy(52.5, 30.0, therapeutic_ratio_range=(1.5, 2.5))
        self.assertEqual(result["status"], "Within supplied range")

    def test_below_supplied_local_range(self):
        result = assess_heparin_therapy(35.0, 30.0, therapeutic_ratio_range=(1.5, 2.5))
        self.assertEqual(result["status"], "Below supplied range")

    def test_above_supplied_local_range(self):
        result = assess_heparin_therapy(100.0, 30.0, therapeutic_ratio_range=(1.5, 2.5))
        self.assertEqual(result["status"], "Above supplied range")

    def test_lmwh_note(self):
        result = assess_heparin_therapy(40.0, 30.0, "lmwh")
        self.assertIn("not titrated by aPTT", result["note"])


class TestProcessBatch(unittest.TestCase):
    def test_batch_factor_deficiency(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "in.csv")
            out = os.path.join(tmp, "out.csv")
            with open(inp, "w") as f:
                f.write("mode,pt,aptt\n")
                f.write("factor_deficiency,16,30\n")
                f.write("factor_deficiency,12,50\n")
            n = process_batch(inp, out)
            self.assertEqual(n, 2)
            with open(out) as f:
                content = f.read()
                self.assertIn("Factor VII", content)

    def test_batch_warfarin(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "in.csv")
            out = os.path.join(tmp, "out.csv")
            with open(inp, "w") as f:
                f.write("mode,inr,indication\n")
                f.write("warfarin,2.5,standard\n")
            n = process_batch(inp, out)
            self.assertEqual(n, 1)


class TestCLI(unittest.TestCase):
    def test_cli_pt(self):
        from cli import main
        self.assertEqual(main(["pt", "--pt", "12.0"]), 0)

    def test_cli_factors(self):
        from cli import main
        self.assertEqual(main(["factors", "--pt", "16", "--aptt", "30"]), 0)

    def test_cli_warfarin(self):
        from cli import main
        self.assertEqual(main(["warfarin", "--inr", "2.5", "--indication", "standard"]), 0)

    def test_cli_heparin(self):
        from cli import main
        self.assertEqual(main(["heparin", "--aptt", "55", "--control-aptt", "30"]), 0)

    def test_cli_mixing(self):
        from cli import main
        self.assertEqual(main(["mixing", "--patient-aptt", "55", "--immediate-mix", "32"]), 0)


if __name__ == "__main__":
    unittest.main()
