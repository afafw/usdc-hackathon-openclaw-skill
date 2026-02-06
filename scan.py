#!/usr/bin/env python3
"""
SafeGuard — Skill Supply-Chain Scanner for OpenClaw
Scans SKILL.md + all scripts in a skill directory for security red flags.

Usage:
    python3 scan.py <skill_dir>          # terminal report
    python3 scan.py <skill_dir> --json   # JSON output
"""

import sys, os, re, hashlib, json, glob
from pathlib import Path

# ── Red flag patterns ────────────────────────────────────────────

PATTERNS = [
    {
        "id": "pipe-to-shell",
        "desc": "Pipe-to-shell execution",
        "regex": r"(curl|wget|fetch)\s+[^\n]*\|\s*(ba)?sh",
        "severity": "critical",
    },
    {
        "id": "credential-read",
        "desc": "Credential / secret file access",
        "regex": r"(~/\.config/|~/\.ssh/|\$HOME/\.config/|\$HOME/\.ssh/|\.env\b|credentials\.json|private[_-]?key|api[_-]?key|MOLTBOOK_API_KEY|OPENAI_API_KEY)",
        "severity": "critical",
    },
    {
        "id": "exfil-outbound",
        "desc": "Outbound data exfiltration",
        "regex": r"(fetch|curl|wget|http\.request|requests\.(get|post))\s*\(\s*['\"]https?://(?!api\.hyperliquid|sepolia\.base\.org|www\.moltbook\.com)",
        "severity": "high",
    },
    {
        "id": "sudo-escalation",
        "desc": "Privilege escalation",
        "regex": r"\b(sudo|chmod\s+777|chown\s+root)\b",
        "severity": "high",
    },
    {
        "id": "eval-exec",
        "desc": "Dynamic code execution",
        "regex": r"\b(eval|exec)\s*\(",
        "severity": "medium",
    },
    {
        "id": "base64-decode",
        "desc": "Base64 decode (potential obfuscation)",
        "regex": r"(base64\s+(-d|--decode)|atob\(|b64decode)",
        "severity": "medium",
    },
    {
        "id": "system-path-write",
        "desc": "Write to system paths",
        "regex": r"(\/etc\/|\/usr\/local\/bin|\/tmp\/.*\.sh)",
        "severity": "medium",
    },
]

# ── Scanner ──────────────────────────────────────────────────────

def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "0x" + h.hexdigest()[:16]


def scan_file(filepath: str) -> list[dict]:
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for pat in PATTERNS:
            if re.search(pat["regex"], line, re.IGNORECASE):
                findings.append({
                    "file": filepath,
                    "line": i,
                    "pattern": pat["id"],
                    "desc": pat["desc"],
                    "severity": pat["severity"],
                    "snippet": line.strip()[:120],
                })
    return findings


def scan_skill(skill_dir: str) -> dict:
    skill_dir = os.path.abspath(skill_dir)
    if not os.path.isdir(skill_dir):
        return {"error": f"Not a directory: {skill_dir}"}

    # Parse SKILL.md for metadata
    skill_md = os.path.join(skill_dir, "SKILL.md")
    name, version = "unknown", "0.0.0"
    if os.path.exists(skill_md):
        with open(skill_md, "r") as f:
            content = f.read()
        m = re.search(r"^name:\s*(.+)$", content, re.M)
        if m:
            name = m.group(1).strip()
        m = re.search(r"^version:\s*(.+)$", content, re.M)
        if m:
            version = m.group(1).strip()

    # Scan all files
    all_findings = []
    all_hashes = {}
    for ext in ("*.md", "*.py", "*.js", "*.ts", "*.sh", "*.bash", "*.yaml", "*.yml", "*.json"):
        for fp in glob.glob(os.path.join(skill_dir, "**", ext), recursive=True):
            if "node_modules" in fp or ".git" in fp:
                continue
            all_hashes[os.path.relpath(fp, skill_dir)] = hash_file(fp)
            all_findings.extend(scan_file(fp))

    # Compute aggregate hash
    combined = hashlib.sha256()
    for k in sorted(all_hashes.keys()):
        combined.update(all_hashes[k].encode())
    pkg_hash = "0x" + combined.hexdigest()[:16]

    # Verdict
    criticals = [f for f in all_findings if f["severity"] == "critical"]
    highs = [f for f in all_findings if f["severity"] == "high"]
    if criticals:
        verdict = "BLOCK"
    elif highs:
        verdict = "BLOCK"
    elif all_findings:
        verdict = "WARN"
    else:
        verdict = "ALLOW"

    return {
        "skill": name,
        "version": version,
        "hash": pkg_hash,
        "verdict": verdict,
        "findings": all_findings,
        "file_hashes": all_hashes,
        "summary": f"{len(criticals)} critical, {len(highs)} high, {len(all_findings) - len(criticals) - len(highs)} other findings",
    }


# ── Pretty output ────────────────────────────────────────────────

COLORS = {
    "BLOCK": "\033[91m",
    "WARN": "\033[93m",
    "ALLOW": "\033[92m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}


def print_report(report: dict):
    c = COLORS
    v = report["verdict"]
    vc = c.get(v, "")

    print()
    print(f"{c['bold']}╔══════════════════════════════════════════════════╗{c['reset']}")
    print(f"{c['bold']}║  SafeGuard Scan Report                           ║{c['reset']}")
    print(f"{c['bold']}╠══════════════════════════════════════════════════╣{c['reset']}")
    print(f"{c['bold']}║  Skill: {report['skill']} v{report['version']:<29}║{c['reset']}")
    print(f"{c['bold']}║  Hash:  {report['hash']:<39}║{c['reset']}")
    print(f"{c['bold']}║{' ' * 50}║{c['reset']}")
    emoji = "🚨" if v == "BLOCK" else "⚠️ " if v == "WARN" else "✅"
    print(f"{c['bold']}║  Verdict: {vc}{emoji} {v}{c['reset']}{c['bold']}{' ' * (36 - len(v))}║{c['reset']}")
    print(f"{c['bold']}║{' ' * 50}║{c['reset']}")

    for f in report["findings"]:
        flag = "🚩" if f["severity"] in ("critical", "high") else "⚠️ "
        rel = os.path.basename(f["file"])
        line = f"  {flag} {rel}:{f['line']}: {f['desc']}"
        if len(line) > 48:
            line = line[:47] + "…"
        print(f"{c['bold']}║{line:<50}║{c['reset']}")
        snip = f"     {c['dim']}{f['snippet'][:44]}{c['reset']}"
        print(f"{c['bold']}║{c['reset']}{snip}")

    if not report["findings"]:
        print(f"{c['bold']}║  No red flags detected.{' ' * 26}║{c['reset']}")

    print(f"{c['bold']}╚══════════════════════════════════════════════════╝{c['reset']}")
    print()


# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scan.py <skill_dir> [--json]")
        sys.exit(1)

    skill_dir = sys.argv[1]
    use_json = "--json" in sys.argv

    report = scan_skill(skill_dir)

    if use_json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    # Exit code: 0 = ALLOW, 1 = WARN, 2 = BLOCK
    sys.exit({"ALLOW": 0, "WARN": 1, "BLOCK": 2}.get(report.get("verdict", ""), 1))
