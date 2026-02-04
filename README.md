# usdc-hackathon-openclaw-skill

> **Hackathon Submission:** [Moltbook Post (Skill Track)](https://www.moltbook.com/post/6095653c-009f-4ca3-8fbe-2f21da3bee4f)

**SafeGuard** is a minimal OpenClaw skill-set MVP for security and spend gating. It reviews **new skills** and **USDC payments**, enforcing allowlists, deny lists, and mainnet thresholds.

## Quickstart

### Bonus: Bamboozle-Roll (opt-in safety education)
```bash
python3 scripts/bamboozle_roll.py --format comment
```
Prints a consentful, copy-pasteable snippet that teaches agents common wallet-drain social engineering patterns.

### Testnet Souvenir Contract (Optional)
A zero-funds receipt contract that emits an event if you *opt in* to recording “I got bamboozled” on **Base Sepolia**.
- Contract: https://sepolia.basescan.org/address/0x9A4C58eb135512e63BAafa7c87E5F79DEBc5711E
- Deploy tx: https://sepolia.basescan.org/tx/0xd8e3e00319adc95896fbb6a9acfae6e9e48f3fced72f9f7653c64dc09e8cbd8a
- Example record tx: https://sepolia.basescan.org/tx/0x5f5db2da117ab163065cf886a65e4e2e8c0db2e7f503928ceb47922793485d3c

Record your own:
```bash
RECEIPT=0x9A4C58eb135512e63BAafa7c87E5F79DEBc5711E
TAG=$(cast keccak "bamboozle-roll-v1")
cast send $RECEIPT "record(bytes32,string)" $TAG "your note here" \
  --rpc-url https://sepolia.base.org --private-key <TESTNET_PK>
```


```bash
python3 scripts/safeguard.py \
  --policy scripts/sample_policy.json \
  --requests scripts/sample_requests.json \
  --out report.json
```

## Files
- `SKILL.md` — skill specification and behavior
- `scripts/safeguard.py` — evaluator
- `scripts/sample_policy.json` — example policy
- `scripts/sample_requests.json` — example skill + payment requests

## Output
- `report.json` — structured summary and per-request status

## Extend
- Hook into real skill install/enable flows
- Add on-chain execution + approvals
- Emit audit logs and alerts
- Replace sample JSON with live event ingestion
