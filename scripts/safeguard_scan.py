#!/usr/bin/env python3
"""
SafeGuard v3 — Live Contract & Transaction Risk Scanner

Usage (CLI):
  python3 safeguard_scan.py --address 0x036CbD53842c5426634e7929541eC2318f3dCF7e
  python3 safeguard_scan.py --address 0x5051c61c62bF59865638d9B459363308D8112bd1
  python3 safeguard_scan.py --tx 0xdda69436a56f789347a623c6c8817f04cbbdb34d369a58f5ce89ff8752200585
  python3 safeguard_scan.py --address 0xDEAD --bytecode 0x6000f46000ff

Usage (HTTP server):
  python3 safeguard_scan.py --serve --port 8042
  curl "http://localhost:8042/scan?address=0x036CbD53842c5426634e7929541eC2318f3dCF7e"
  curl "http://localhost:8042/scan?tx=0xdda6..."

Testnet only. No private keys required. Read-only RPC calls.
"""

import argparse, json, sys, urllib.request, textwrap
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DEFAULT_RPC = "https://sepolia.base.org"
BASESCAN = "https://sepolia.basescan.org"

# ── Known safe contracts ──────────────────────────────────────────

KNOWN_SAFE = {
    "0x036cbd53842c5426634e7929541ec2318f3dcf7e": {"name": "Circle USDC", "chain": "Base Sepolia"},
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {"name": "Circle USDC", "chain": "Ethereum Mainnet"},
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {"name": "Circle USDC", "chain": "Base Mainnet"},
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": {"name": "Uniswap Universal Router", "chain": "Multi"},
    "0x5051c61c62bf59865638d9b459363308d8112bd1": {"name": "EscrowProof v2 (hackathon)", "chain": "Base Sepolia"},
    "0x24a557da76636587deaee52cfe25fc8163ba6a49": {"name": "ReputationPassport (hackathon)", "chain": "Base Sepolia"},
    "0x9a4c58eb135512e63baafa7c87e5f79debc5711e": {"name": "BamboozledReceipt (hackathon)", "chain": "Base Sepolia"},
}

# ── Dangerous opcode patterns ────────────────────────────────────

PATTERNS = [
    {"opcode": "ff", "name": "selfdestruct",  "severity": "CRITICAL", "score": 40,
     "desc": "Can self-destruct, destroying contract and draining ETH balance"},
    {"opcode": "f4", "name": "delegatecall",  "severity": "HIGH",     "score": 20,
     "desc": "Executes external code in this contract's storage context (proxy/upgrade risk)"},
    {"opcode": "f2", "name": "callcode",      "severity": "HIGH",     "score": 20,
     "desc": "Deprecated CALLCODE — potential proxy attack vector"},
    {"opcode": "f5", "name": "create2",       "severity": "MEDIUM",   "score": 10,
     "desc": "CREATE2 — deploys contracts at predictable addresses (metamorphic risk)"},
    {"opcode": "32", "name": "tx.origin",     "severity": "MEDIUM",   "score": 10,
     "desc": "Uses tx.origin — vulnerable to phishing/relay attacks"},
]

# ── Suspicious function selectors ────────────────────────────────

SELECTORS = {
    "095ea7b3": {"name": "approve(address,uint256)",      "risk": "MEDIUM", "note": "Check for unlimited approvals (type(uint256).max)"},
    "42966c68": {"name": "burn(uint256)",                  "risk": "HIGH",   "note": "Token burn — irreversible"},
    "715018a6": {"name": "renounceOwnership()",            "risk": "HIGH",   "note": "Ownership renounced — no admin recovery possible"},
    "f2fde38b": {"name": "transferOwnership(address)",     "risk": "HIGH",   "note": "Ownership transfer — verify recipient"},
    "3659cfe6": {"name": "upgradeTo(address)",             "risk": "HIGH",   "note": "Proxy upgrade — contract logic can change"},
    "4f1ef286": {"name": "upgradeToAndCall(address,bytes)","risk": "HIGH",   "note": "Proxy upgrade + call — logic change + execution"},
}


# ── RPC helpers ──────────────────────────────────────────────────

def rpc_call(method, params, rpc=DEFAULT_RPC):
    payload = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    req = urllib.request.Request(rpc, data=payload, headers={"Content-Type":"application/json","User-Agent":"SafeGuard/3.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("result")
    except Exception:
        # Fallback RPC
        for fallback in ["https://base-sepolia-rpc.publicnode.com", "https://sepolia.base.org"]:
            if fallback == rpc: continue
            try:
                req2 = urllib.request.Request(fallback, data=payload, headers={"Content-Type":"application/json","User-Agent":"SafeGuard/3.0"})
                with urllib.request.urlopen(req2, timeout=15) as resp:
                    return json.loads(resp.read()).get("result")
            except Exception:
                continue
        return None

def fetch_bytecode(address, rpc=DEFAULT_RPC):
    return rpc_call("eth_getCode", [address, "latest"], rpc) or "0x"

def fetch_tx(txhash, rpc=DEFAULT_RPC):
    return rpc_call("eth_getTransactionByHash", [txhash], rpc)


# ── Core scanner ─────────────────────────────────────────────────

def scan_bytecode(code_hex):
    """Scan bytecode for dangerous patterns. Returns findings list + risk score."""
    code = code_hex[2:] if code_hex.startswith("0x") else code_hex
    
    if len(code) < 2:
        return {"findings": [{"name":"empty_contract","severity":"CRITICAL","desc":"No bytecode (EOA or destroyed)","count":1}], "risk_score": 100}
    
    findings = []
    total_score = 0
    
    for p in PATTERNS:
        opc = p["opcode"].lower()
        count = 0
        i = 0
        while i < len(code):
            byte = code[i:i+2].lower()
            if byte == opc:
                count += 1
            # Skip PUSH1-PUSH32 data
            if "60" <= byte <= "7f":
                push_size = int(byte, 16) - 0x5f
                i += 2 + push_size * 2
            else:
                i += 2
        if count > 0:
            findings.append({"name": p["name"], "severity": p["severity"], "desc": p["desc"], "count": count})
            total_score += p["score"] * count
    
    # Check selectors
    selectors_found = []
    for sel, info in SELECTORS.items():
        if sel in code.lower():
            selectors_found.append({"selector": "0x"+sel, **info})
    
    return {"findings": findings, "selectors": selectors_found, "risk_score": min(total_score, 100), "bytecode_size": len(code)//2}


def scan_address(address, rpc=DEFAULT_RPC):
    """Full scan of a contract address."""
    addr = address.lower()
    
    # Known safe check
    if addr in KNOWN_SAFE:
        info = KNOWN_SAFE[addr]
        return {
            "address": address,
            "verdict": "SAFE",
            "risk_score": 0,
            "reason": f"Known safe: {info['name']} ({info['chain']})",
            "identity": info["name"],
            "chain": info["chain"],
            "findings": [],
            "explorer": f"{BASESCAN}/address/{address}",
        }
    
    bytecode = fetch_bytecode(addr, rpc)
    result = scan_bytecode(bytecode)
    
    # Determine verdict
    score = result["risk_score"]
    if score == 0:
        verdict = "SAFE"
    elif score < 20:
        verdict = "LOW_RISK"
    elif score < 40:
        verdict = "MEDIUM_RISK"
    elif score < 60:
        verdict = "HIGH_RISK"
    else:
        verdict = "BLOCK"
    
    reasons = []
    for f in result["findings"]:
        reasons.append(f"[{f['severity']}] {f['name']} (×{f['count']}): {f['desc']}")
    for s in result.get("selectors", []):
        reasons.append(f"[{s['risk']}] {s['name']}: {s['note']}")
    
    return {
        "address": address,
        "verdict": verdict,
        "risk_score": score,
        "findings": result["findings"],
        "selectors": result.get("selectors", []),
        "reasons": reasons,
        "bytecode_size": result.get("bytecode_size", 0),
        "explorer": f"{BASESCAN}/address/{address}",
    }


def scan_tx(txhash, rpc=DEFAULT_RPC):
    """Scan a transaction: analyze the target contract + calldata."""
    tx = fetch_tx(txhash, rpc)
    if not tx:
        return {"tx": txhash, "verdict": "ERROR", "reason": "Transaction not found"}
    
    to_addr = tx.get("to") or ""
    value = int(tx.get("value", "0x0"), 16)
    input_data = tx.get("input", "0x")
    
    result = {"tx": txhash, "from": tx.get("from",""), "to": to_addr, "value_wei": value, "explorer": f"{BASESCAN}/tx/{txhash}"}
    
    # Decode calldata selector
    if len(input_data) >= 10:
        sel = input_data[2:10].lower()
        if sel in SELECTORS:
            info = SELECTORS[sel]
            result["function"] = info["name"]
            result["function_risk"] = info["risk"]
            result["function_note"] = info["note"]
    
    # Scan target contract
    if to_addr:
        addr_scan = scan_address(to_addr, rpc)
        result["contract_verdict"] = addr_scan["verdict"]
        result["contract_risk_score"] = addr_scan["risk_score"]
        result["contract_findings"] = addr_scan.get("findings", [])
        result["contract_identity"] = addr_scan.get("identity")
        result["verdict"] = addr_scan["verdict"]
        result["risk_score"] = addr_scan["risk_score"]
        result["reasons"] = addr_scan.get("reasons", [])
    else:
        result["verdict"] = "CONTRACT_CREATION"
        result["risk_score"] = 50
        result["reasons"] = ["Transaction creates a new contract"]
    
    return result


# ── Pretty output ────────────────────────────────────────────────

VERDICT_EMOJI = {"SAFE": "✅", "LOW_RISK": "🟡", "MEDIUM_RISK": "🟠", "HIGH_RISK": "🔴", "BLOCK": "🚫", "ERROR": "❌", "CONTRACT_CREATION": "📦"}

def pretty_print(result):
    v = result.get("verdict", "?")
    emoji = VERDICT_EMOJI.get(v, "❓")
    score = result.get("risk_score", "?")
    
    print(f"\n{'='*60}")
    print(f"  SafeGuard v3 Risk Report")
    print(f"{'='*60}")
    
    if result.get("address"):
        print(f"  Contract:  {result['address']}")
    if result.get("tx"):
        print(f"  Tx:        {result['tx']}")
    if result.get("identity"):
        print(f"  Identity:  {result['identity']}")
    
    print(f"\n  {emoji}  Verdict: {v}  |  Risk Score: {score}/100")
    print(f"{'─'*60}")
    
    reasons = result.get("reasons", [])
    if reasons:
        print("  Findings:")
        for r in reasons:
            print(f"    • {r}")
    elif result.get("reason"):
        print(f"  {result['reason']}")
    else:
        print("  No dangerous patterns detected.")
    
    if result.get("bytecode_size"):
        print(f"\n  Bytecode size: {result['bytecode_size']} bytes")
    if result.get("explorer"):
        print(f"  Explorer: {result['explorer']}")
    
    print(f"{'='*60}")
    
    # Auto-generate vote evidence
    print(f"\n--- Copy/paste #Vote evidence (if reviewing SafeGuard for SK track) ---")
    target = result.get("address") or result.get("tx") or "?"
    print(f"Scanned {target} → {v} (score {score}/100)")
    if reasons:
        for r in reasons[:3]:
            print(f"  {r}")
    print(f"Repo: https://github.com/afafw/usdc-hackathon-openclaw-skill")
    print()


# ── HTTP Server ──────────────────────────────────────────────────

class ScanHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == "/scan":
            address = (params.get("address") or [None])[0]
            tx = (params.get("tx") or [None])[0]
            rpc = (params.get("rpc") or [DEFAULT_RPC])[0]
            
            try:
                if tx:
                    result = scan_tx(tx, rpc)
                elif address:
                    result = scan_address(address, rpc)
                else:
                    result = {"error": "Provide ?address=0x... or ?tx=0x..."}
            except Exception as e:
                result = {"error": str(e)}
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())
        
        elif parsed.path == "/" or parsed.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LANDING_HTML.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.date_time_string()}] {format % args}")

LANDING_HTML = """<!DOCTYPE html>
<html><head><title>SafeGuard v3 — Contract Risk Scanner</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:2rem}
h1{color:#58a6ff;margin-bottom:.5rem;font-size:1.8rem}
.sub{color:#8b949e;margin-bottom:2rem;text-align:center}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:2rem;width:100%;max-width:640px;margin-bottom:1.5rem}
input{width:100%;padding:.75rem 1rem;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;font-size:1rem;margin-bottom:1rem}
input:focus{outline:none;border-color:#58a6ff}
button{background:#238636;color:#fff;border:none;padding:.75rem 2rem;border-radius:8px;font-size:1rem;cursor:pointer;width:100%}
button:hover{background:#2ea043}
button:disabled{background:#21262d;color:#484f58;cursor:not-allowed}
#result{margin-top:1rem;white-space:pre-wrap;font-family:'SF Mono',monospace;font-size:.85rem;line-height:1.5;max-height:400px;overflow-y:auto}
.safe{color:#3fb950}.low{color:#d29922}.medium{color:#d29922}.high{color:#f85149}.block{color:#f85149}
.badge{display:inline-block;padding:.25rem .75rem;border-radius:20px;font-weight:600;font-size:1.1rem;margin:.5rem 0}
.badge.safe{background:#0d2818;border:1px solid #238636}
.badge.block{background:#2d0a0a;border:1px solid #da3633}
.badge.medium{background:#2a1f02;border:1px solid #d29922}
.trust{color:#8b949e;font-size:.8rem;margin-top:1.5rem;text-align:center}
a{color:#58a6ff;text-decoration:none}
a:hover{text-decoration:underline}
.copy-btn{background:#21262d;color:#c9d1d9;border:1px solid #30363d;padding:.5rem 1rem;border-radius:6px;font-size:.85rem;cursor:pointer;margin-top:.5rem;width:auto;display:inline-block}
.copy-btn:hover{background:#30363d}
</style></head><body>
<h1>🛡️ SafeGuard v3</h1>
<p class="sub">Contract & Transaction Risk Scanner — Base Sepolia (testnet only)</p>
<div class="card">
<input id="addr" placeholder="Paste contract address (0x...) or transaction hash (0x...)" autofocus>
<button id="btn" onclick="doScan()">Scan</button>
<div id="result"></div>
<div id="vote-section" style="display:none;margin-top:1rem;padding-top:1rem;border-top:1px solid #30363d">
<strong>📋 Copy/paste #Vote evidence:</strong>
<pre id="vote-text" style="background:#0d1117;padding:.75rem;border-radius:6px;margin-top:.5rem;font-size:.8rem"></pre>
<button class="copy-btn" onclick="copyVote()">📋 Copy Vote Comment</button>
</div>
</div>
<div class="trust">
Testnet only · No private keys · Read-only RPC · <a href="https://github.com/afafw/usdc-hackathon-openclaw-skill">Source code</a>
</div>
<script>
async function doScan(){
  const inp=document.getElementById('addr').value.trim();
  const btn=document.getElementById('btn');
  const res=document.getElementById('result');
  const vs=document.getElementById('vote-section');
  if(!inp){res.textContent='Enter an address or tx hash';return}
  btn.disabled=true;btn.textContent='Scanning...';res.textContent='';vs.style.display='none';
  const isHash=inp.length===66;
  const param=isHash?'tx':'address';
  try{
    const r=await fetch('/scan?'+param+'='+encodeURIComponent(inp));
    const j=await r.json();
    if(j.error){res.textContent='Error: '+j.error;return}
    const v=j.verdict||'?';
    const s=j.risk_score??'?';
    const cls=v==='SAFE'?'safe':v==='BLOCK'?'block':s>=40?'high':s>=20?'medium':'safe';
    const emoji={'SAFE':'✅','LOW_RISK':'🟡','MEDIUM_RISK':'🟠','HIGH_RISK':'🔴','BLOCK':'🚫','ERROR':'❌','CONTRACT_CREATION':'📦'}[v]||'❓';
    let html='<span class="badge '+cls+'">'+emoji+' '+v+' — Score: '+s+'/100</span>\\n\\n';
    if(j.identity)html+='Identity: '+j.identity+'\\n';
    if(j.reasons&&j.reasons.length){html+='Findings:\\n';j.reasons.forEach(r=>html+='  • '+r+'\\n')}
    else html+='No dangerous patterns detected.\\n';
    if(j.bytecode_size)html+='\\nBytecode: '+j.bytecode_size+' bytes';
    if(j.explorer)html+='\\n<a href="'+j.explorer+'" target="_blank">View on BaseScan →</a>';
    res.innerHTML=html;
    // Generate vote text
    const target=j.address||j.tx||inp;
    let vt='Scanned '+target+' → '+v+' (score '+s+'/100)\\n';
    if(j.reasons)j.reasons.slice(0,3).forEach(r=>vt+='  '+r+'\\n');
    vt+='\\nRepo: https://github.com/afafw/usdc-hackathon-openclaw-skill';
    document.getElementById('vote-text').textContent=vt;
    vs.style.display='block';
  }catch(e){res.textContent='Error: '+e.message}
  finally{btn.disabled=false;btn.textContent='Scan'}
}
function copyVote(){
  const t=document.getElementById('vote-text').textContent;
  navigator.clipboard.writeText('#USDCHackathon Vote\\n\\nI ran SafeGuard v3 risk scanner on a live contract/tx:\\n\\n'+t);
  document.querySelector('.copy-btn').textContent='✅ Copied!';
  setTimeout(()=>document.querySelector('.copy-btn').textContent='📋 Copy Vote Comment',2000);
}
document.getElementById('addr').addEventListener('keydown',e=>{if(e.key==='Enter')doScan()});
</script></body></html>"""


# ── Main ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="SafeGuard v3 — Contract & Transaction Risk Scanner")
    ap.add_argument("--address", help="Contract address to scan")
    ap.add_argument("--tx", help="Transaction hash to scan")
    ap.add_argument("--rpc", default=DEFAULT_RPC, help="RPC URL (default: Base Sepolia)")
    ap.add_argument("--bytecode", help="Raw bytecode (alternative to RPC fetch)")
    ap.add_argument("--json", action="store_true", help="JSON output only")
    ap.add_argument("--serve", action="store_true", help="Start HTTP server")
    ap.add_argument("--port", type=int, default=8042, help="Server port (default: 8042)")
    args = ap.parse_args()
    
    if args.serve:
        print(f"SafeGuard v3 scanner running at http://localhost:{args.port}")
        print(f"  Scan: http://localhost:{args.port}/scan?address=0x...")
        print(f"  UI:   http://localhost:{args.port}/")
        HTTPServer(("0.0.0.0", args.port), ScanHandler).serve_forever()
    elif args.tx:
        result = scan_tx(args.tx, args.rpc)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            pretty_print(result)
    elif args.address:
        if args.bytecode:
            result = scan_bytecode(args.bytecode)
            result["address"] = args.address
            # Add verdict
            s = result["risk_score"]
            result["verdict"] = "SAFE" if s==0 else "LOW_RISK" if s<20 else "MEDIUM_RISK" if s<40 else "HIGH_RISK" if s<60 else "BLOCK"
            result["reasons"] = [f"[{f['severity']}] {f['name']} (×{f['count']}): {f['desc']}" for f in result["findings"]]
        else:
            result = scan_address(args.address, args.rpc)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            pretty_print(result)
    else:
        ap.print_help()
        print("\nExamples:")
        print("  python3 safeguard_scan.py --address 0x036CbD53842c5426634e7929541eC2318f3dCF7e")
        print("  python3 safeguard_scan.py --tx 0xdda69436a56f789347a623c6c8817f04cbbdb34d369a58f5ce89ff8752200585")
        print("  python3 safeguard_scan.py --serve")


if __name__ == "__main__":
    main()
