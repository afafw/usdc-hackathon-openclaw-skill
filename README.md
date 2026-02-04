# usdc-hackathon-openclaw-skill

SpendGuard is a minimal OpenClaw skill-track MVP for USDC policy gating. It evaluates a batch of transactions against a simple policy file and produces approvals with reasons.

## Quickstart
```bash
python3 scripts/spendguard.py \
  --policy scripts/sample_policy.json \
  --transactions scripts/sample_transactions.csv \
  --out report.json
```

## Files
- `SKILL.md` — skill specification and behavior
- `scripts/spendguard.py` — evaluator
- `scripts/sample_policy.json` — example policy
- `scripts/sample_transactions.csv` — example transactions

## Output
- `report.json` — structured summary and per-transaction status

## Extend
- Swap CSV for live expense ingestion
- Add on-chain execution + approvals
- Wire to notifications / dashboards
