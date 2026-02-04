---
name: safeguard
description: Skill-set gatekeeper for new skills and USDC payments. Enforces allowlists/denylists and mainnet thresholds.
---

# SafeGuard (USDC Skill Track MVP)

A minimal OpenClaw skill-set that reviews **new skill installs/enables** and **USDC payment requests** against a policy. Designed for hackathon demos and safe-by-default behavior.

## What it does
- Reads a **policy JSON** (allowlists, denylists, risky permissions, mainnet thresholds)
- Reads **requests JSON** (skills + payments)
- Flags each request as **APPROVE / REVIEW / DENY**
- Writes a structured JSON report for the agent to summarize

## Inputs
- `scripts/sample_policy.json`
- `scripts/sample_requests.json`

## Outputs
- `report.json` (default)
- stdout summary

## Usage
```bash
python3 scripts/safeguard.py \
  --policy scripts/sample_policy.json \
  --requests scripts/sample_requests.json \
  --out report.json
```

## Decision Rules (MVP)
**Skills**
- **DENY**: author/source on denylist
- **REVIEW**: not on allowlist (if allowlist is configured), or risky permissions requested

**Payments**
- **DENY**: recipient on denylist, or mainnet disabled
- **REVIEW**: recipient not on allowlist (if configured), exceeds single-tx limit, exceeds mainnet threshold

## Files
- `scripts/safeguard.py` — core evaluator
- `scripts/sample_policy.json` — example policy
- `scripts/sample_requests.json` — example requests

## Next Steps (Ideas)
- Hook into real skill install/enable flows
- Add on-chain execution + approvals
- Emit audit logs and alerts
- Add risk scoring & anomaly detection
