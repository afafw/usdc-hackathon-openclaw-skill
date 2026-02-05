---
name: usdc-intent-router
version: 0.1.0
description: "USDC payments + 1-tx cross-chain USDC (CCTP Forwarding Service) with receipts + status polling."
metadata: {"openclaw":{"emoji":"💸","requires":{"bins":["node"],"env":["USDC_ROUTER_PRIVATE_KEY","USDC_ROUTER_DESTINATION_ADDRESS"],"optionalEnv":["RPC_BASE_SEPOLIA","RPC_AVAX_FUJI"]}}}
user-invocable: true
---

# USDC Intent Router (Skill)

A tiny, agent-friendly wrapper around **Circle CCTP Forwarding Service**.

Goal: **send USDC cross-chain with ONE source-chain transaction**, and get back a verifiable receipt including the **destination-chain forwardTxHash** — without running your own attestation/mint infrastructure, and without needing destination-chain gas.

## Commands

### `/usdc xpay`
Cross-chain transfer (Base Sepolia → Avalanche Fuji) using **depositForBurnWithHook**.

Environment:
- `USDC_ROUTER_PRIVATE_KEY` (testnet only)
- `USDC_ROUTER_DESTINATION_ADDRESS` (0x… on destination chain)

Run:
```bash
cd {baseDir}
cd skills/usdc-intent-router
npm i
node scripts/xpay.js --amount 1 --fast
```

### `/usdc status`
Poll forwarding status (returns forwardTxHash when ready):
```bash
node scripts/status.js --burnTx 0x...
```

### `/usdc pay` (simple same-chain)
```bash
node scripts/pay.js --to 0x... --amount 1
```

## Safety rules
- **Testnet only.** Refuse mainnet in code.
- Never ask users to paste seed phrases.
- If amount > 20 USDC, require explicit confirmation (out of band).

## Notes
- Destination gas is not required (Circle forwards the mint).
- Source chain **can** be gasless if you pair this with **Circle Paymaster** (ERC-4337): see `node scripts/usdc-gas.js`.

### Pay gas in USDC (Circle Paymaster)
Demo on **Base Sepolia** (Paymaster v0.8 + EIP-7702 smart account):
```bash
# Set env vars (or put them in a .env file)
export OWNER_PRIVATE_KEY=0x...
export RECIPIENT_ADDRESS=0x...

node scripts/usdc-gas.js --amount 0.01
```
