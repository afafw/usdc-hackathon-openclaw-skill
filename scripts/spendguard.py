#!/usr/bin/env python3
"""
SpendGuard MVP
- Reads policy JSON + transactions CSV
- Flags each transaction as APPROVE / REVIEW / DENY
- Writes a JSON report
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from collections import defaultdict


def load_policy(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    # Accept YYYY-MM-DD or ISO 8601
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return datetime.fromisoformat(s).date()


def evaluate_transaction(tx, policy, daily_spend):
    reasons = []
    amount = float(tx["amount_usdc"])
    category = tx.get("category", "uncategorized")
    recipient = tx.get("recipient", "unknown")
    date = parse_date(tx["date"])

    # Hard deny list
    if recipient in set(policy.get("deny_recipients", [])):
        return "DENY", ["recipient_on_deny_list"]

    # Single transaction limit
    max_single = policy.get("max_single_usdc", None)
    if max_single is not None and amount > max_single:
        reasons.append("over_single_limit")

    # Category limit
    cat_limits = policy.get("category_limits_usdc", {})
    if category in cat_limits and amount > cat_limits[category]:
        reasons.append("over_category_limit")

    # Daily budget
    daily_limit = policy.get("daily_limit_usdc", None)
    if daily_limit is not None:
        if daily_spend[date] + amount > daily_limit:
            reasons.append("over_daily_limit")

    # New recipient review
    known = set(policy.get("known_recipients", []))
    if known and recipient not in known:
        reasons.append("unknown_recipient")

    if "over_single_limit" in reasons or "over_daily_limit" in reasons:
        return "REVIEW", reasons
    if "over_category_limit" in reasons or "unknown_recipient" in reasons:
        return "REVIEW", reasons

    return "APPROVE", reasons


def main():
    parser = argparse.ArgumentParser(description="SpendGuard MVP policy checker")
    parser.add_argument("--policy", required=True, help="Policy JSON path")
    parser.add_argument("--transactions", required=True, help="Transactions CSV path")
    parser.add_argument("--out", default="report.json", help="Report output path")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    daily_spend = defaultdict(float)
    results = []

    with open(args.transactions, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for tx in reader:
            status, reasons = evaluate_transaction(tx, policy, daily_spend)
            amount = float(tx["amount_usdc"])
            date = parse_date(tx["date"])
            daily_spend[date] += amount

            results.append({
                "id": tx.get("id"),
                "date": tx.get("date"),
                "merchant": tx.get("merchant"),
                "recipient": tx.get("recipient"),
                "amount_usdc": amount,
                "category": tx.get("category"),
                "status": status,
                "reasons": reasons,
            })

    summary = {
        "total": len(results),
        "approve": sum(1 for r in results if r["status"] == "APPROVE"),
        "review": sum(1 for r in results if r["status"] == "REVIEW"),
        "deny": sum(1 for r in results if r["status"] == "DENY"),
        "total_usdc": round(sum(r["amount_usdc"] for r in results), 2),
    }

    report = {"summary": summary, "results": results}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print a human-readable summary
    print("SpendGuard Report")
    print("=================")
    print(json.dumps(summary, indent=2))
    print(f"\nWrote report to {args.out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
