import { createWalletClient, http, encodeFunctionData, parseUnits } from "viem";
import { baseSepolia } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

const BASE_SEPOLIA_USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";

function getArg(flag) {
  const i = process.argv.indexOf(flag);
  if (i === -1) return null;
  return process.argv[i + 1] ?? null;
}

async function main() {
  const to = getArg("--to");
  const amountStr = getArg("--amount") ?? "1";

  const pk = process.env.USDC_ROUTER_PRIVATE_KEY;
  const rpc = process.env.RPC_BASE_SEPOLIA || "https://sepolia.base.org";

  if (!pk) throw new Error("Missing env USDC_ROUTER_PRIVATE_KEY");
  if (!to) throw new Error("Usage: node scripts/pay.js --to 0x... --amount 1");

  // Hard safety gate: testnet only.
  if (!rpc.includes("sepolia")) {
    throw new Error(`Refusing non-testnet RPC: ${rpc}`);
  }

  const account = privateKeyToAccount((pk.startsWith("0x") ? pk : `0x${pk}`));
  const client = createWalletClient({ chain: baseSepolia, transport: http(rpc), account });

  const amount = parseUnits(amountStr, 6);

  const data = encodeFunctionData({
    abi: [
      {
        type: "function",
        name: "transfer",
        stateMutability: "nonpayable",
        inputs: [
          { name: "to", type: "address" },
          { name: "amount", type: "uint256" },
        ],
        outputs: [{ name: "", type: "bool" }],
      },
    ],
    functionName: "transfer",
    args: [to, amount],
  });

  const tx = await client.sendTransaction({ to: BASE_SEPOLIA_USDC, data });
  console.log("tx:", tx);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
