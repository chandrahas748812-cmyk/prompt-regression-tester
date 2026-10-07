# Prompt Regression Tester

A **Git-based prompt registry with automated CI regression gates**. Prompts live as versioned YAML files; every change runs a regression suite against a fixed test set and blocks merges that degrade quality past a threshold.

## The problem it solves

Prompt edits are code changes, but most teams edit them like config — no tests, no review, silent regressions in production. This gives prompts the same safety rails as code.

## How it works

```
prompts/
  summarizer.v1.yaml ─┐
  summarizer.v2.yaml ─┴─▶ registry loads all versions
                              │
                              ▼
                    regression.py runs each version
                    against tests/cases.jsonl
                              │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              all metrics within      regression detected
              tolerance → PASS        → FAIL (blocks merge)
```

## Quickstart

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
# run the regression suite for a prompt
python src/regression.py --prompt summarizer --baseline v1 --candidate v2
```

## Prompt file format (YAML)

```yaml
name: summarizer
version: v2
model: gpt-4o-mini
temperature: 0
system: |
  Summarize the following text in 2 sentences or fewer.
  Preserve all numbers and dates exactly.
changelog: "Tightened length constraint; added number preservation rule."
```

## Regression gates

| Metric | Gate |
|--------|------|
| ROUGE-L vs expected | candidate ≥ baseline − 0.05 |
| Avg output length | within ±30% of baseline |
| Empty / refusal rate | must not increase |

Exit code 0 = safe to merge. Exit code 1 = regression, block the PR.

## CI example (GitHub Actions)

```yaml
- name: Prompt regression check
  run: python src/regression.py --prompt ${{ matrix.prompt }} --baseline main --candidate HEAD
```

## Project layout

```
src/
  registry.py     # Loads versioned YAML prompts, diffs versions
  regression.py   # Runs cases, scores, enforces gates, exit codes
prompts/
  summarizer.v1.yaml
  summarizer.v2.yaml
tests/
  cases.jsonl     # Fixed regression cases (never change these)
```

## Built with

Python · PyYAML · OpenAI API · rouge-score
