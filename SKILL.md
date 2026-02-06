---
name: safeguard
version: 2.0.0
description: Scan any OpenClaw skill for security red flags before installation. Block malicious skills, track version drift, attest results on-chain.
homepage: https://github.com/afafw/usdc-hackathon-openclaw-skill
metadata:
  openclaw:
    requires:
      bins: ["python3"]
    category: security
---

# SafeGuard — Skill Supply-Chain Security for OpenClaw

**Pay only after safe install.**

SafeGuard scans OpenClaw skills (SKILL.md + scripts) for security red flags *before* your agent installs them. Think `npm audit` but for agent skills.

## What it catches

- 🚩 **Pipe-to-shell** (`curl ... | bash`, `wget ... | sh`)
- 🚩 **Credential access** (reads `~/.config/*`, `$HOME/.ssh/*`, env vars with KEY/TOKEN/SECRET)
- 🚩 **Data exfiltration** (outbound fetch/curl to unknown domains)
- 🚩 **Version drift** (hash changed between versions = unexpected mutation)
- 🚩 **Privilege escalation** (`sudo`, `chmod 777`, writing to system paths)

## Usage

```bash
# Scan a skill directory
python3 scan.py ./path/to/skill/

# Scan with on-chain attestation (Base Sepolia)
python3 scan.py ./path/to/skill/ --attest

# Output: structured JSON report
python3 scan.py ./path/to/skill/ --json
```

## Output Format

```
╔══════════════════════════════════════════╗
║  SafeGuard Scan Report                   ║
╠══════════════════════════════════════════╣
║  Skill: weather-lookup v1.1.0            ║
║  Hash:  0xd4c1...8f3a                    ║
║                                          ║
║  Verdict: 🚨 BLOCK                       ║
║                                          ║
║  🚩 Line 12: curl ... | bash             ║
║  🚩 Line 18: reads ~/.config/creds.json  ║
║  🚩 Line 23: fetch to evil.example.com   ║
║  🚩 Hash drift: 0x9a3f → 0xd4c1          ║
╚══════════════════════════════════════════╝
```

## Install

Copy this directory to your OpenClaw skills folder:
```bash
cp -r safeguard/ ~/.openclaw/skills/safeguard/
```

Or clone directly:
```bash
git clone https://github.com/afafw/usdc-hackathon-openclaw-skill ~/.openclaw/skills/safeguard
```

## Integration with InstallToPay

SafeGuard is the verification layer in the [InstallToPay](https://usdc-hackathon-agentic-commerce.vercel.app) escrow flow:

1. Buyer locks USDC in escrow
2. Seller delivers skill package
3. **SafeGuard scans the skill** ← you are here
4. If ALLOW → USDC releases
5. If BLOCK → dispute + on-chain evidence

## On-Chain Attestation

Scan results can be attested on Base Sepolia via ReputationPassport:
- Passport: [`0x8cF1FAE51Fffae83aB63f354a152256B62828E1E`](https://sepolia.basescan.org/address/0x8cF1FAE51Fffae83aB63f354a152256B62828E1E)
