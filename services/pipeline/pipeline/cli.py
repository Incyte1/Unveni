from __future__ import annotations

import argparse
import json

from pipeline.backtest import backtest_plan
from pipeline.config import default_config
from pipeline.features import build_candidate_set
from pipeline.ingest import build_ingestion_plan
from pipeline.train import training_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Unveni pipeline control plane")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("plan", help="Show the full pipeline plan")
    subparsers.add_parser("ingest-plan", help="Show ingestion jobs")
    subparsers.add_parser("build-candidates", help="Show candidate build output")
    subparsers.add_parser("train", help="Show training configuration")
    subparsers.add_parser("backtest", help="Show backtest configuration")
    subparsers.add_parser("loop", help="Show one orchestrated daily cycle")

    args = parser.parse_args()
    config = default_config()

    if args.command == "plan":
        payload = {
            "pipeline": config.to_dict(),
            "ingestion": build_ingestion_plan(),
            "candidates": build_candidate_set(config.candidate_build),
            "training": training_plan(config.training),
            "backtest": backtest_plan(config.backtest)
        }
    elif args.command == "ingest-plan":
        payload = build_ingestion_plan()
    elif args.command == "build-candidates":
        payload = build_candidate_set(config.candidate_build)
    elif args.command == "train":
        payload = training_plan(config.training)
    elif args.command == "backtest":
        payload = backtest_plan(config.backtest)
    else:
        payload = {
            "06:15_ct": "ingest overnight and macro data",
            "06:40_ct": "rebuild candidate trades and run risk gates",
            "07:00_ct": "publish ranked opportunities",
            "15:20_ct": "prepare closing rebalance and reports"
        }

    print(json.dumps(payload, indent=2))
    return 0
