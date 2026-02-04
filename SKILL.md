---
name: safeguard
description: Security gatekeeper for OpenClaw agents — reviews skills, USDC payments, and smart contracts before interaction.
---

# SafeGuard v2 (USDC Skill Track)

A security-first OpenClaw skill that protects agents from malicious skills, dangerous contracts, and risky USDC transfers. Combines policy-based gating with on-chain bytecode analysis.

## What it does

### 1. Skill & Payment Gating (v1)
- Reads a **policy JSON** (allowlists, denylists, risky permissions, mainnet thresholds)
- Reviews **skill installs** and **USDC payment requests**
- Flags each request as **APPROVE / REVIEW / DENY**

### 2. Contract Bytecode Scanner (v2 — NEW)
- Fetches on-chain bytecode via RPC or accepts raw bytecode
- Scans for **dangerous opcodes**: selfdestruct, delegatecall, callcode, tx.origin
- Detects **known function selectors**: approve, transferFrom, burn, renounceOwnership
- Matches against **known safe contracts** (USDC, Uniswap Router)
- Outputs a **risk score** (0-100) and **risk level** (APPROVE/REVIEW/DENY)

Inspired by Sentinel AI Auditor and USDC Security Scanner from the USDC Hackathon.

## Usage

### Policy Gate
```bash
python3 scripts/safeguard.py \
  --policy scripts/sample_policy.json \
  --requests scripts/sample_requests.json \
  --out report.json
```

### Contract Scanner
```bash
# Scan by bytecode (fetched via cast/curl)
BYTECODE=$(cast code 0xCONTRACT --rpc-url https://sepolia.base.org)
python3 scripts/contract_scanner.py --bytecode "$BYTECODE"

# Scan known safe address (instant lookup)
python3 scripts/contract_scanner.py --address 0x036CbD53842c5426634e7929541eC2318f3dCF7e
```

### Example Output (Contract Scanner)
```json
{
  "bytecodeSize": 9453,
  "riskScore": 20,
  "riskLevel": "REVIEW",
  "findings": [
    {
      "name": "delegatecall",
      "severity": "HIGH",
      "description": "Uses delegatecall — can execute arbitrary code in context",
      "occurrences": 1
    }
  ],
  "knownSelectors": [
    {"name": "transfer(address,uint256)", "risk": "LOW"},
    {"name": "transferOwnership(address)", "risk": "HIGH"}
  ]
}
```

## Decision Rules

### Skills
- **DENY**: author/source on denylist
- **REVIEW**: not on allowlist, or risky permissions (filesystem, network, exec)

### Payments
- **DENY**: recipient on denylist, or mainnet disabled
- **REVIEW**: recipient not on allowlist, exceeds single-tx or mainnet threshold

### Contracts
- **APPROVE**: known safe (USDC, Uniswap) — instant
- **DENY**: selfdestruct detected, risk score ≥ 60
- **REVIEW**: delegatecall, high-risk selectors, risk score 20-59

## Files
- `scripts/safeguard.py` — policy evaluator (skills + payments)
- `scripts/contract_scanner.py` — bytecode analyzer (NEW)
- `scripts/sample_policy.json` — example policy config
- `scripts/sample_requests.json` — example requests

## Architecture
```
Agent Request → SafeGuard
                ├── Policy Gate (skills/payments)
                │   └── allowlist/denylist/thresholds
                └── Contract Scanner (NEW)
                    ├── bytecode fetch (RPC)
                    ├── opcode analysis
                    ├── selector detection
                    └── known-safe lookup
```

## Bonus (Opt-in): Bamboozle-Roll
A **consentful social-engineering test vector** that helps agents practice refusing:
- secret requests (PK/seed)
- mainnet prompts
- random shell commands
- unlimited approvals

Generate a shareable snippet:
```bash
python3 scripts/bamboozle_roll.py --format comment
python3 scripts/bamboozle_roll.py --format post
```

Constraints:
- Explicitly labeled link (no deception)
- No auto-posting; only prints text for humans/agents to copy-paste
- No vote requests

## What's Next
- Hook into real OpenClaw skill install/enable flows
- Add Etherscan-verified source code analysis
- Combine policy gate + contract scanner into unified pipeline
- Real-time monitoring: flag when approved contracts get upgraded
- Risk scoring with ML-based anomaly detection
