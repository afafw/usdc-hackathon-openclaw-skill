function getArg(flag) {
  const i = process.argv.indexOf(flag);
  if (i === -1) return null;
  return process.argv[i + 1] ?? null;
}

async function main() {
  const burnTx = getArg("--burnTx");
  if (!burnTx) throw new Error("Usage: node scripts/status.js --burnTx 0x...");

  const baseSepoliaDomain = 6;
  const url = `https://iris-api-sandbox.circle.com/v2/messages/${baseSepoliaDomain}?transactionHash=${burnTx}`;

  const res = await fetch(url);
  if (!res.ok) throw new Error(`Iris messages query failed: ${res.status}`);
  const data = await res.json();

  const msg = data?.messages?.[0];
  if (!msg) {
    console.log(JSON.stringify(data, null, 2));
    console.log("No messages yet (or unexpected response). Try again in ~2-10s.");
    return;
  }

  console.log("burnTx:", burnTx);
  console.log("status:", msg.status);
  console.log("cctpVersion:", msg.cctpVersion);
  console.log("eventNonce:", msg.eventNonce);

  const decoded = msg.decodedMessage || {};
  console.log("sourceDomain:", decoded.sourceDomain ?? "(unknown)");
  console.log("destinationDomain:", decoded.destinationDomain ?? "(unknown)");
  console.log("minFinalityThreshold:", decoded.minFinalityThreshold ?? "(unknown)");

  console.log("attestation:", msg.attestation ? "present" : "(not yet)");
  console.log("forwardTxHash:", msg.forwardTxHash ?? "(not yet)");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
