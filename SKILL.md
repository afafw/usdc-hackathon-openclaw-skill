---
name: spendguard
description: MVP policy gate for USDC spending. Evaluates transactions against limits and outputs approve/review/deny decisions with reasons.
---

# SpendGuard (USDC Skill Track MVP)

A minimal OpenClaw skill that checks USDC transactions against a policy file and produces approvals with explanations. Designed for hackathon demos and easy extension to real on-chain flows.

## What it does
- Reads a **policy JSON** (limits, known/deny recipients)
- Reads **transactions CSV**
- Flags each transaction as **APPROVE / REVIEW / DENY**
- Writes a structured JSON report for the agent to summarize

## Inputs
- `scripts/sample_policy.json`
- `scripts/sample_transactions.csv`

## Outputs
- `report.json` (default)
- stdout summary

## Usage
```bash
python3 scripts/spendguard.py \
  --policy scripts/sample_policy.json \
  --transactions scripts/sample_transactions.csv \
  --out report.json
```

## Decision Rules (MVP)
- **DENY**: recipient on deny list
- **REVIEW**: over single limit, over category limit, over daily limit, or unknown recipient
- **APPROVE**: otherwise

## Files
- `scripts/spendguard.py` — core evaluator
- `scripts/sample_policy.json` — example policy
- `scripts/sample_transactions.csv` — example transactions

## Next Steps (Ideas)
- Integrate live USDC transfers (Circle, Coinbase, or on-chain)
- Add webhook approvals + audit trails
- Replace CSV with ingestion from expense systems
- Add risk scoring & anomaly detection
