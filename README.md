# usdc-hackathon-openclaw-skill

**SafeGuard** is a minimal OpenClaw skill-set MVP for security and spend gating. It reviews **new skills** and **USDC payments**, enforcing allowlists, deny lists, and mainnet thresholds.

## Quickstart
```bash
python3 scripts/safeguard.py \
  --policy scripts/sample_policy.json \
  --requests scripts/sample_requests.json \
  --out report.json
```

## Files
- `SKILL.md` — skill specification and behavior
- `scripts/safeguard.py` — evaluator
- `scripts/sample_policy.json` — example policy
- `scripts/sample_requests.json` — example skill + payment requests

## Output
- `report.json` — structured summary and per-request status

## Extend
- Hook into real skill install/enable flows
- Add on-chain execution + approvals
- Emit audit logs and alerts
- Replace sample JSON with live event ingestion
