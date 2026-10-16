"""Run the RAG evaluation:  python -m app.eval_cli [--k 5] [--retrieval-only]

Uses the configured embedding model and LLM. Results are stored and appear on the Analytics page."""

import argparse
import json

from app.db.session import SessionLocal
from app.services import eval_service


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=None)
    p.add_argument("--retrieval-only", action="store_true", help="skip LLM answers (no answer-level metrics)")
    args = p.parse_args()
    with SessionLocal() as db:
        run = eval_service.run_evaluation(db, k=args.k, answers=False if args.retrieval_only else None)
        print(json.dumps({"run_id": run.id, "status": run.status, "mode": run.mode, "error": run.error, "metrics": run.metrics}, indent=2))


if __name__ == "__main__":
    main()
