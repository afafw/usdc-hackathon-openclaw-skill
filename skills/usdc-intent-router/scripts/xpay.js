import { createWalletClient, http, encodeFunctionData, pad, parseUnits, formatUnits } from "viem";
import { baseSepolia } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

const BASE_SEPOLIA_DOMAIN = 6;
const AVALANCHE_FUJI_DOMAIN = 1;

// Circle docs (Forwarding Service how-to)
const BASE_SEPOLIA_USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
const BASE_SEPOLIA_TOKEN_MESSENGER_V2 = "0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA";

const FORWARDING_SERVICE_HOOK_DATA =
  "0x636374702d666f72776172640000000000000000000000000000000000000000";

function getArg(flag) {
  const i = process.argv.indexOf(flag);
  if (i === -1) return null;
  return process.argv[i + 1] ?? null;
}

function hasFlag(flag) {
  return process.argv.includes(flag);
}

async function getFees({ fast }) {
  const url = `https://iris-api-sandbox.circle.com/v2/burn/USDC/fees/${BASE_SEPOLIA_DOMAIN}/${AVALANCHE_FUJI_DOMAIN}?forward=true`;
  const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error(`fee fetch failed: ${res.status}`);
  const fees = await res.json();
  // fees[0] = fast (finalityThreshold 1000), fees[1] = standard (2000)
  return fast ? fees[0] : fees[1];
}

function computeMaxFee({ feeData, forwardTier = "med" }) {
  const forwardFee = BigInt(feeData.forwardFee[forwardTier]);
  // minimumFee is in cents of USDC; convert to 6-decimal subunits.
  const protocolFee = BigInt(Math.floor(Number(feeData.minimumFee) * 10_000));
  return { forwardFee, protocolFee, maxFee: forwardFee + protocolFee, minFinalityThreshold: feeData.finalityThreshold };
}

async function approveUSDC({ client, amount }) {
  const data = encodeFunctionData({
    abi: [
      {
        type: "function",
        name: "approve",
        stateMutability: "nonpayable",
        inputs: [
          { name: "spender", type: "address" },
          { name: "amount", type: "uint256" },
        ],
        outputs: [{ name: "", type: "bool" }],
      },
    ],
    functionName: "approve",
    args: [BASE_SEPOLIA_TOKEN_MESSENGER_V2, amount],
  });

  return client.sendTransaction({
    to: BASE_SEPOLIA_USDC,
    data,
  });
}

async function depositForBurnWithHook({ client, totalAmount, mintRecipient, maxFee, minFinalityThreshold }) {
  const data = encodeFunctionData({
    abi: [
      {
        type: "function",
        name: "depositForBurnWithHook",
        stateMutability: "nonpayable",
        inputs: [
          { name: "amount", type: "uint256" },
          { name: "destinationDomain", type: "uint32" },
          { name: "mintRecipient", type: "bytes32" },
          { name: "burnToken", type: "address" },
          { name: "destinationCaller", type: "bytes32" },
          { name: "maxFee", type: "uint256" },
          { name: "minFinalityThreshold", type: "uint32" },
          { name: "hookData", type: "bytes" },
        ],
        outputs: [],
      },
    ],
    functionName: "depositForBurnWithHook",
    args: [
      totalAmount,
      AVALANCHE_FUJI_DOMAIN,
      mintRecipient,
      BASE_SEPOLIA_USDC,
      pad("0x", { size: 32 }),
      maxFee,
      Number(minFinalityThreshold),
      FORWARDING_SERVICE_HOOK_DATA,
    ],
  });

  return client.sendTransaction({
    to: BASE_SEPOLIA_TOKEN_MESSENGER_V2,
    data,
  });
}

async function main() {
  const amountStr = getArg("--amount") ?? "1";
  const fast = hasFlag("--fast");
  const forwardTier = getArg("--forwardTier") ?? "med";

  const pk = process.env.USDC_ROUTER_PRIVATE_KEY;
  const dest = process.env.USDC_ROUTER_DESTINATION_ADDRESS;
  const rpc = process.env.RPC_BASE_SEPOLIA || "https://sepolia.base.org";

  if (!pk) throw new Error("Missing env USDC_ROUTER_PRIVATE_KEY");
  if (!dest) throw new Error("Missing env USDC_ROUTER_DESTINATION_ADDRESS");
  if (!dest.startsWith("0x") || dest.length !== 42) throw new Error("DESTINATION_ADDRESS must be an EVM 0x address");

  // Hard safety gate: testnet only.
  if (!rpc.includes("sepolia")) {
    throw new Error(`Refusing non-testnet RPC: ${rpc}`);
  }

  const account = privateKeyToAccount((pk.startsWith("0x") ? pk : `0x${pk}`));
  const client = createWalletClient({ chain: baseSepolia, transport: http(rpc), account });

  const transferAmount = parseUnits(amountStr, 6);

  console.log("wallet:", account.address);
  console.log("dest  :", dest);

  const feeData = await getFees({ fast });
  const { forwardFee, protocolFee, maxFee, minFinalityThreshold } = computeMaxFee({ feeData, forwardTier });

  const totalAmount = transferAmount + maxFee;

  console.log("--- fees ---");
  console.log("transferAmount:", formatUnits(transferAmount, 6), "USDC");
  console.log("forwardFee    :", formatUnits(forwardFee, 6), "USDC");
  console.log("protocolFee   :", formatUnits(protocolFee, 6), "USDC");
  console.log("maxFee        :", formatUnits(maxFee, 6), "USDC");
  console.log("total burn    :", formatUnits(totalAmount, 6), "USDC");
  console.log("finality      :", minFinalityThreshold);

  const mintRecipient = pad(dest, { size: 32 });

  console.log("\n1) approve...");
  const approveTx = await approveUSDC({ client, amount: totalAmount });
  console.log("approveTx:", approveTx);

  console.log("\n2) burn (depositForBurnWithHook)...");
  const burnTx = await depositForBurnWithHook({
    client,
    totalAmount,
    mintRecipient,
    maxFee,
    minFinalityThreshold,
  });
  console.log("burnTx:", burnTx);

  console.log("\n3) status polling hint:");
  console.log(`node scripts/status.js --burnTx ${burnTx}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
