#!/usr/bin/env python3
"""
SafeGuard Contract Scanner — Analyzes EVM bytecode for dangerous patterns.
Inspired by Sentinel AI Auditor and USDC Security Scanner from the hackathon.

Usage:
  python3 contract_scanner.py --address 0x... --rpc https://sepolia.base.org
  python3 contract_scanner.py --bytecode 0x6080...
"""

import argparse, json, sys, urllib.request

# ── Dangerous bytecode patterns ───────────────────────────────────

PATTERNS = [
    {
        "name": "selfdestruct",
        "opcode": "ff",
        "severity": "CRITICAL",
        "description": "Contract can self-destruct, draining all funds"
    },
    {
        "name": "delegatecall",
        "opcode": "f4",
        "severity": "HIGH",
        "description": "Uses delegatecall — can execute arbitrary code in contract context"
    },
    {
        "name": "callcode",
        "opcode": "f2",
        "severity": "HIGH",
        "description": "Uses deprecated CALLCODE — potential proxy attack vector"
    },
    {
        "name": "create2",
        "opcode": "f5",
        "severity": "MEDIUM",
        "description": "Uses CREATE2 — can deploy contracts at predictable addresses"
    },
    {
        "name": "tx.origin",
        "opcode": "32",
        "severity": "MEDIUM",
        "description": "Uses tx.origin — vulnerable to phishing attacks"
    },
]

# ── Known malicious function signatures ───────────────────────────

SUSPICIOUS_SELECTORS = {
    "0xa9059cbb": {"name": "transfer(address,uint256)", "risk": "LOW", "note": "Standard ERC20 — check context"},
    "0x095ea7b3": {"name": "approve(address,uint256)", "risk": "MEDIUM", "note": "Approval — check for unlimited approvals"},
    "0x70a08231": {"name": "balanceOf(address)", "risk": "LOW", "note": "Read-only"},
    "0x23b872dd": {"name": "transferFrom(address,address,uint256)", "risk": "MEDIUM", "note": "Requires prior approval"},
    "0x42966c68": {"name": "burn(uint256)", "risk": "HIGH", "note": "Token burn — irreversible"},
    "0x715018a6": {"name": "renounceOwnership()", "risk": "HIGH", "note": "Ownership renounced — no admin recovery"},
    "0xf2fde38b": {"name": "transferOwnership(address)", "risk": "HIGH", "note": "Ownership transfer — check recipient"},
}

# ── Known safe contract hashes (USDC, common DEX routers) ─────────

KNOWN_SAFE = {
    "0x036cbd53842c5426634e7929541ec2318f3dcf7e": "Circle USDC (Base Sepolia)",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "Circle USDC (Ethereum Mainnet)",
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "Circle USDC (Base Mainnet)",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap Universal Router",
}


def fetch_bytecode(address, rpc_url):
    """Fetch contract bytecode via eth_getCode RPC call."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1
    }).encode()

    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    return data.get("result", "0x")


def scan_bytecode(bytecode):
    """Scan bytecode for dangerous patterns."""
    findings = []
    # Strip 0x prefix
    code = bytecode[2:] if bytecode.startswith("0x") else bytecode

    if len(code) < 2:
        return [{"name": "empty_contract", "severity": "CRITICAL",
                 "description": "Contract has no bytecode (EOA or destroyed)"}]

    # Check for dangerous opcodes
    for pattern in PATTERNS:
        # Simple opcode scan (single-byte opcodes)
        opcode = pattern["opcode"].lower()
        # Walk through bytecode looking for the opcode outside of PUSH data
        i = 0
        count = 0
        while i < len(code):
            byte = code[i:i+2].lower()
            if byte == opcode:
                count += 1
            # Skip PUSH1-PUSH32 data bytes
            if byte >= "60" and byte <= "7f":
                push_size = int(byte, 16) - 0x5f
                i += 2 + push_size * 2
            else:
                i += 2

        if count > 0:
            findings.append({
                "name": pattern["name"],
                "severity": pattern["severity"],
                "description": pattern["description"],
                "occurrences": count
            })

    # Check for known function selectors in bytecode
    selectors_found = []
    for selector, info in SUSPICIOUS_SELECTORS.items():
        sel_hex = selector[2:]  # strip 0x
        if sel_hex in code:
            selectors_found.append({**info, "selector": selector})

    # Calculate risk score
    severity_scores = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
    risk_score = sum(severity_scores.get(f["severity"], 0) * f.get("occurrences", 1)
                     for f in findings)

    # Risk level
    if risk_score >= 60:
        risk_level = "DENY"
    elif risk_score >= 20:
        risk_level = "REVIEW"
    else:
        risk_level = "APPROVE"

    return {
        "bytecodeSize": len(code) // 2,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "findings": findings,
        "knownSelectors": selectors_found
    }


def main():
    ap = argparse.ArgumentParser(description="SafeGuard Contract Scanner")
    ap.add_argument("--address", help="Contract address to scan")
    ap.add_argument("--rpc", default="https://sepolia.base.org", help="RPC URL")
    ap.add_argument("--bytecode", help="Raw bytecode to scan (alternative to address)")
    ap.add_argument("--out", help="Output JSON file")
    args = ap.parse_args()

    address = (args.address or "").lower()

    # Check known safe contracts
    if address in KNOWN_SAFE:
        result = {
            "address": address,
            "status": "KNOWN_SAFE",
            "identity": KNOWN_SAFE[address],
            "riskLevel": "APPROVE",
            "riskScore": 0
        }
    elif args.bytecode:
        result = scan_bytecode(args.bytecode)
        result["source"] = "bytecode_input"
    elif args.address:
        bytecode = fetch_bytecode(args.address, args.rpc)
        result = scan_bytecode(bytecode)
        result["address"] = args.address
    else:
        print("Error: provide --address or --bytecode", file=sys.stderr)
        sys.exit(1)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
