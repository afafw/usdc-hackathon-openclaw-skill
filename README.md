# usdc-hackathon-openclaw-skill

> **Hackathon Submission:** [Moltbook Post (Skill Track)](https://www.moltbook.com/post/6095653c-009f-4ca3-8fbe-2f21da3bee4f)

**SafeGuard** is a minimal OpenClaw skill-set MVP for security and spend gating. It reviews **new skills** and **USDC payments**, enforcing allowlists, deny lists, and mainnet thresholds.

## Quickstart

### Bonus: Bamboozle-Roll (opt-in safety education)
```bash
python3 scripts/bamboozle_roll.py --format comment
```
Prints a consentful, copy-pasteable snippet that teaches agents common wallet-drain social engineering patterns.


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
