"""Regression runner: score candidate prompt vs baseline, enforce gates.

Usage:
    python src/regression.py --prompt summarizer --baseline v1 --candidate v2

Exit 0 = no regression (safe to merge). Exit 1 = regression detected.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from rouge_score import rouge_scorer

from .registry import load_prompt

CASES = Path(__file__).parent.parent / "tests" / "cases.jsonl"
_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

# Gate tolerances
ROUGE_TOLERANCE = 0.05   # candidate rougeL >= baseline - 0.05
LENGTH_TOLERANCE = 0.30  # avg length within ±30%


def run_cases(prompt, cases: list[dict]) -> list[dict]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    results = []
    for case in cases:
        resp = client.chat.completions.create(
            model=prompt.model,
            temperature=prompt.temperature,
            messages=prompt.render(case["input"]),
            max_tokens=300,
        )
        output = resp.choices[0].message.content
        rouge = _scorer.score(case["expected"], output)["rougeL"].fmeasure
        results.append({"output": output, "rougeL": rouge, "length": len(output)})
    return results


def check_gates(baseline: list[dict], candidate: list[dict]) -> tuple[bool, list[str]]:
    failures = []
    b_rouge = sum(r["rougeL"] for r in baseline) / len(baseline)
    c_rouge = sum(r["rougeL"] for r in candidate) / len(candidate)
    if c_rouge < b_rouge - ROUGE_TOLERANCE:
        failures.append(f"ROUGE-L regressed: {b_rouge:.3f} → {c_rouge:.3f} (tolerance {ROUGE_TOLERANCE})")

    b_len = sum(r["length"] for r in baseline) / len(baseline)
    c_len = sum(r["length"] for r in candidate) / len(candidate)
    if abs(c_len - b_len) / max(b_len, 1) > LENGTH_TOLERANCE:
        failures.append(f"Length drifted: {b_len:.0f} → {c_len:.0f} chars (tolerance ±{LENGTH_TOLERANCE:.0%})")

    b_empty = sum(1 for r in baseline if not r["output"].strip())
    c_empty = sum(1 for r in candidate if not r["output"].strip())
    if c_empty > b_empty:
        failures.append(f"Empty outputs increased: {b_empty} → {c_empty}")

    return (len(failures) == 0, failures)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    args = ap.parse_args()

    with open(CASES) as f:
        cases = [json.loads(line) for line in f if line.strip()]

    base_prompt = load_prompt(args.prompt, args.baseline)
    cand_prompt = load_prompt(args.prompt, args.candidate)

    print(f"Baseline: {args.prompt}.{args.baseline}  →  Candidate: {args.prompt}.{args.candidate}")
    print(f"Running {len(cases)} regression cases...\n")

    base_results = run_cases(base_prompt, cases)
    cand_results = run_cases(cand_prompt, cases)

    passed, failures = check_gates(base_results, cand_results)
    if passed:
        print("✅ PASS — no regression detected. Safe to merge.")
        sys.exit(0)
    print("❌ FAIL — regression detected:")
    for f_ in failures:
        print(f"  - {f_}")
    sys.exit(1)


if __name__ == "__main__":
    main()
