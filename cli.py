#!/usr/bin/env python3
"""
CLI for Coagulation Cascade Calculator & Interpreter.

Usage:
  python cli.py pt --pt 15.0
  python cli.py inr --inr 2.5 --context warfarin_standard
  python cli.py aptt --aptt 45 --control-aptt 30 --heparin
  python cli.py mixing --patient-aptt 55 --immediate-mix 38 --incubated-mix 50 --control-aptt 30
  python cli.py factors --pt 16 --aptt 50
  python cli.py warfarin --inr 2.8 --indication standard
  python cli.py heparin --aptt 55 --control-aptt 30
  python cli.py batch -i input.csv -o results.csv
"""
import argparse
import json
import sys

from coag_sentinel import (
    interpret_pt,
    interpret_inr,
    interpret_aptt,
    interpret_mixing_study,
    identify_factor_deficiency,
    assess_warfarin_dose,
    assess_heparin_therapy,
    process_batch,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="coag-cascade",
        description="Coagulation Cascade Calculator & Interpreter",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # PT
    p_pt = subparsers.add_parser("pt", help="Interpret PT")
    p_pt.add_argument("--pt", type=float, required=True, help="PT in seconds")

    # INR
    p_inr = subparsers.add_parser("inr", help="Interpret INR")
    p_inr.add_argument("--inr", type=float, required=True, help="INR value")
    p_inr.add_argument("--context", default=None,
                       help="Therapeutic context: warfarin_standard, warfarin_mechanical_valve")

    # aPTT
    p_aptt = subparsers.add_parser("aptt", help="Interpret aPTT")
    p_aptt.add_argument("--aptt", type=float, required=True, help="aPTT in seconds")
    p_aptt.add_argument("--control-aptt", type=float, default=None, help="Control aPTT")
    p_aptt.add_argument("--heparin", action="store_true", help="Heparin monitoring mode")

    # Mixing study
    p_mix = subparsers.add_parser("mixing", help="Interpret mixing study")
    p_mix.add_argument("--patient-aptt", type=float, required=True, help="Patient aPTT")
    p_mix.add_argument("--immediate-mix", type=float, required=True, help="Immediate mix aPTT")
    p_mix.add_argument("--incubated-mix", type=float, default=None, help="2-hour incubated mix aPTT")
    p_mix.add_argument("--control-aptt", type=float, default=30.0, help="Control aPTT")

    # Factor deficiency
    p_fac = subparsers.add_parser("factors", help="Identify factor deficiency pattern")
    p_fac.add_argument("--pt", type=float, required=True, help="PT in seconds")
    p_fac.add_argument("--aptt", type=float, required=True, help="aPTT in seconds")
    p_fac.add_argument("--tt", type=float, default=None, help="Thrombin time (optional)")

    # Warfarin
    p_war = subparsers.add_parser("warfarin", help="Warfarin dose assessment")
    p_war.add_argument("--inr", type=float, required=True, help="Current INR")
    p_war.add_argument("--indication", default="standard",
                       help="Indication: standard or mechanical_valve")
    p_war.add_argument("--previous-inr", type=float, default=None, help="Previous INR")
    p_war.add_argument("--dose", type=float, default=None, help="Current weekly dose (mg)")

    # Heparin
    p_hep = subparsers.add_parser("heparin", help="Heparin therapy assessment")
    p_hep.add_argument("--aptt", type=float, required=True, help="Patient aPTT")
    p_hep.add_argument("--control-aptt", type=float, required=True, help="Control aPTT")
    p_hep.add_argument("--type", default="unfractionated", help="Heparin type")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV")
    p_batch.add_argument("-i", "--input", required=True, help="Input CSV")
    p_batch.add_argument("-o", "--output", default="results.csv", help="Output CSV")

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run supervisor audit on task")
    p_audit.add_argument("--task-id", default="CLI-AUDIT-01", help="Task ID")
    p_audit.add_argument("--target", default="KEY-01", help="Target identifier")
    p_audit.add_argument("--primary", type=float, default=12.0, help="Primary metric")
    p_audit.add_argument("--secondary", type=float, default=4.0, help="Secondary metric")
    p_audit.add_argument("--status", default="NOMINAL", help="Status descriptor")

    # Chat
    p_chat = subparsers.add_parser("chat", help="Supervisory chat query")
    p_chat.add_argument("query", nargs="+", help="Query string")

    # Verify Audit
    p_v_audit = subparsers.add_parser("verify-audit", help="Verify cryptographic audit trail")

    args = parser.parse_args(argv)

    if args.command == "pt":
        print(json.dumps(interpret_pt(args.pt), indent=2))
    elif args.command == "inr":
        print(json.dumps(interpret_inr(args.inr, args.context), indent=2))
    elif args.command == "aptt":
        print(json.dumps(interpret_aptt(args.aptt, args.control_aptt, args.heparin), indent=2))
    elif args.command == "mixing":
        print(json.dumps(interpret_mixing_study(
            args.patient_aptt, args.immediate_mix, args.incubated_mix, args.control_aptt,
        ), indent=2))
    elif args.command == "factors":
        print(json.dumps(identify_factor_deficiency(args.pt, args.aptt, args.tt), indent=2))
    elif args.command == "warfarin":
        print(json.dumps(assess_warfarin_dose(
            args.inr, args.indication, args.previous_inr, args.dose,
        ), indent=2))
    elif args.command == "heparin":
        print(json.dumps(assess_heparin_therapy(args.aptt, args.control_aptt, args.type), indent=2))
    elif args.command == "batch":
        n = process_batch(args.input, args.output)
        print(f"Processed {n} records -> {args.output}")
    elif args.command == "audit":
        from agents.supervisor import SystemSupervisor
        from agents.models import SystemTaskPayload
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
        )
        dossier = supervisor.process_task(payload)
        print(json.dumps(dossier.model_dump(), indent=2))
    elif args.command == "chat":
        from agents.supervisor import SystemSupervisor
        supervisor = SystemSupervisor(model_provider="mock")
        response = supervisor.query_supervisory_chat(" ".join(args.query))
        print(response)
    elif args.command == "verify-audit":
        from agents.base import AuditLogger
        ok = AuditLogger.verify_integrity()
        print(f"Audit trail integrity verified: {ok}")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
