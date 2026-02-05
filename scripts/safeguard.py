#!/usr/bin/env python3
import argparse, json, sys
from datetime import datetime, timezone

DEFAULT_DECISION = "REVIEW"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def decision(rank):
    # rank: 0 approve, 1 review, 2 deny
    return ["APPROVE", "REVIEW", "DENY"][rank]


def max_decision(a, b):
    order = {"APPROVE": 0, "REVIEW": 1, "DENY": 2}
    return a if order[a] >= order[b] else b


def eval_skill(skill, policy):
    reasons = []
    d = "APPROVE"
    allow_authors = set(policy.get("allowlist", {}).get("skill_authors", []))
    deny_authors = set(policy.get("denylist", {}).get("skill_authors", []))
    allow_sources = set(policy.get("allowlist", {}).get("skill_sources", []))
    deny_sources = set(policy.get("denylist", {}).get("skill_sources", []))

    author = skill.get("author", "").strip()
    source = skill.get("source", "").strip()

    if author in deny_authors or source in deny_sources:
        return "DENY", ["Denied author/source"]

    if author and author not in allow_authors and allow_authors:
        d = "REVIEW"; reasons.append("Author not in allowlist")

    if source and source not in allow_sources and allow_sources:
        d = max_decision(d, "REVIEW"); reasons.append("Source not in allowlist")

    risky = set(skill.get("requested_permissions", [])) & set(policy.get("risky_permissions", []))
    if risky:
        d = max_decision(d, "REVIEW"); reasons.append(f"Risky permissions: {sorted(risky)}")

    if policy.get("block_new_skills", False):
        d = max_decision(d, "REVIEW"); reasons.append("Block new skills enabled")

    return d, reasons or ["OK"]


def eval_payment(tx, policy):
    reasons = []
    d = "APPROVE"
    chain = tx.get("chain", "").lower()
    amount = float(tx.get("amount", 0))
    to_addr = (tx.get("to", "") or "").lower()

    deny_addrs = set(a.lower() for a in policy.get("denylist", {}).get("addresses", []))
    allow_addrs = set(a.lower() for a in policy.get("allowlist", {}).get("addresses", []))

    if to_addr in deny_addrs:
        return "DENY", ["Recipient denylisted"]

    if allow_addrs and to_addr not in allow_addrs:
        d = max_decision(d, "REVIEW"); reasons.append("Recipient not in allowlist")

    if chain == "mainnet":
        if not policy.get("mainnet_allowed", False):
            return "DENY", ["Mainnet disabled"]
        max_mainnet = float(policy.get("mainnet_max_usdc", 0))
        if amount > max_mainnet:
            d = max_decision(d, "REVIEW"); reasons.append("Exceeds mainnet threshold")

    max_single = float(policy.get("max_single_usdc", 0))
    if max_single and amount > max_single:
        d = max_decision(d, "REVIEW"); reasons.append("Exceeds single-tx limit")

    return d, reasons or ["OK"]


def main():
    ap = argparse.ArgumentParser(description="SafeGuard policy gate for skills + USDC payments")
    ap.add_argument("--policy", required=True)
    ap.add_argument("--requests", required=True, help="JSON with skills[] and payments[]")
    ap.add_argument("--out", default="report.json")
    args = ap.parse_args()

    policy = load_json(args.policy)
    req = load_json(args.requests)

    skills = req.get("skills", [])
    payments = req.get("payments", [])

    skill_reports = []
    for s in skills:
        d, reasons = eval_skill(s, policy)
        skill_reports.append({"name": s.get("name"), "decision": d, "reasons": reasons})

    payment_reports = []
    for p in payments:
        d, reasons = eval_payment(p, policy)
        payment_reports.append({"id": p.get("id"), "decision": d, "reasons": reasons})

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "skills": skill_reports,
        "payments": payment_reports
    }

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
