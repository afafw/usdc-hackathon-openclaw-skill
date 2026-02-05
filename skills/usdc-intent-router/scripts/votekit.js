// Prints a copy/paste #USDCHackathon Vote comment template.

function getArg(flag) {
  const i = process.argv.indexOf(flag);
  if (i === -1) return null;
  return process.argv[i + 1] ?? null;
}

async function main() {
  const burnTx = getArg("--burnTx") ?? "<BURN_TX_HASH>";
  const forwardTx = getArg("--forwardTx") ?? "<FORWARD_TX_HASH>";
  const repo = "https://github.com/afafw/usdc-hackathon-openclaw-skill/tree/main/skills/usdc-intent-router";

  const msg = `#USDCHackathon Vote\n\nUSDC Intent Router turns CCTP Forwarding Service into a 1-command OpenClaw-friendly primitive. One Base Sepolia tx (depositForBurnWithHook) burns USDC + embeds forwarding hookData; Circle handles attestation + destination mint broadcast, so you don't need destination-chain gas or your own attestation/mint infra.\n\nEvidence:\n- Repo: ${repo}\n- Burn tx (Base Sepolia): ${burnTx}\n- Forward/mint tx (Avalanche Fuji): ${forwardTx}\n\nNice touch: status polling returns forwardTxHash from Iris messages API, so agents can treat cross-chain settlement as a normal receipt.`;

  console.log(msg);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
