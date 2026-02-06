#!/usr/bin/env python3
"""SafeGuard v3 — skill.md / README red-team scanner

Purpose:
- Detect *prompt-injection-like* exfil instructions in skill docs (skill.md / SKILL.md / README.md)
- Flag obvious secret paths, command-execution instructions, and suspicious endpoints

This is NOT a full sandbox. It's a cheap static preflight that helps humans/agents decide
whether a skill doc needs deeper audit.

Usage:
  python3 scripts/skillmd_scanner.py --path redteam/malicious_skill.md
  python3 scripts/skillmd_scanner.py --path SKILL.md

Output: JSON with findings + riskScore + verdict.
"""

import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


RULES = [
    {
        "id": "secret_paths",
        "severity": "CRITICAL",
        "score": 40,
        "patterns": [
            r"~\/\.ssh\/id_rsa",
            r"~\/\.ssh\/",
            r"~\/\.env\b",
            r"\.openclaw\/openclaw\.json",
            r"\.clawdbot\/\.env",
            r"OPENAI_API_KEY",
            r"ANTHROPIC_API_KEY",
            r"MOLTBOOK_API_KEY",
        ],
        "desc": "Mentions common secret locations / API keys",
    },
    {
        "id": "exfil_endpoints",
        "severity": "HIGH",
        "score": 20,
        "patterns": [
            r"webhook\.site",
            r"requestbin",
            r"ngrok",
            r"pastebin",
            r"http[s]?://[^\s\)\]]+",
        ],
        "desc": "Mentions external endpoints (possible exfil)",
    },
    {
        "id": "command_exec",
        "severity": "HIGH",
        "score": 20,
        "patterns": [
            r"\bbash\b",
            r"\bsh\b",
            r"\bzsh\b",
            r"\bchmod\b",
            r"\bcurl\b",
            r"\bwget\b",
            r"python\s*-c",
            r"node\s*-e",
            r"exec\(" ,
        ],
        "desc": "Contains instructions that can execute arbitrary commands",
    },
    {
        "id": "safety_bypass",
        "severity": "MEDIUM",
        "score": 10,
        "patterns": [
            r"ignore your safety",
            r"disable safety",
            r"ignore policy",
            r"this is required",
        ],
        "desc": "Attempts to coerce bypassing safety/policy",
    },
]


def scan(text: str):
    findings = []
    total = 0

    for rule in RULES:
        hits = []
        for pat in rule["patterns"]:
            m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                hits.append(pat)
        if hits:
            findings.append({
                "id": rule["id"],
                "severity": rule["severity"],
                "score": rule["score"],
                "desc": rule["desc"],
                "hits": hits[:5],
            })
            total += rule["score"]

    total = min(total, 100)

    if total >= 60:
        verdict = "DENY"
    elif total >= 20:
        verdict = "REVIEW"
    else:
        verdict = "APPROVE"

    return verdict, total, findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    args = ap.parse_args()

    text = load_text(args.path)
    verdict, score, findings = scan(text)

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "path": args.path,
        "verdict": verdict,
        "riskScore": score,
        "findings": findings,
    }

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
