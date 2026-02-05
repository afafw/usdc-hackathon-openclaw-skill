#!/usr/bin/env node
/**
 * Demo: Pay gas fees in USDC using Circle Paymaster (ERC-4337) + a 7702 smart account.
 *
 * Based on Circle docs quickstart (Paymaster v0.8) + viem/account-abstraction.
 *
 * Default chain: Base Sepolia
 *
 * Env:
 *   OWNER_PRIVATE_KEY        (hex, with or without 0x)
 *   RECIPIENT_ADDRESS        (0x...)
 * Optional env:
 *   RPC_URL                  (default: https://sepolia.base.org)
 *   USDC_ADDRESS             (default: Base Sepolia USDC)
 *   PAYMASTER_V08_ADDRESS    (default: Circle Paymaster v0.8 on Base Sepolia)
 *
 * Usage:
 *   node scripts/usdc-gas.js --amount 0.01 --to 0x...
 */

import {
  createPublicClient,
  encodePacked,
  erc20Abi,
  getContract,
  hexToBigInt,
  http,
  maxUint256,
  parseErc6492Signature,
} from "viem";
import { baseSepolia } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import { createBundlerClient, toSimple7702SmartAccount } from "viem/account-abstraction";

const DEFAULTS = {
  rpcUrl: "https://sepolia.base.org",
  // Base Sepolia USDC (6 decimals)
  usdcAddress: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  // Circle Paymaster v0.8 (testnet) — see: https://developers.circle.com/paymaster/addresses-and-events
  paymasterV08: "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
  recipient: "0x1111111111111111111111111111111111111111",
  amountUsdc: "0.01",
};

function getArg(flag) {
  const i = process.argv.indexOf(flag);
  if (i === -1) return undefined;
  return process.argv[i + 1];
}

function normalizePk(pk) {
  if (!pk) return pk;
  return pk.startsWith("0x") ? pk : `0x${pk}`;
}

function parseUsdcAmount(amountStr) {
  // 6 decimals
  const s = String(amountStr ?? "").trim();
  if (!s) throw new Error("Missing amount");
  if (!/^[0-9]+(\.[0-9]+)?$/.test(s)) throw new Error(`Invalid amount: ${s}`);
  const [whole, frac = ""] = s.split(".");
  const fracPadded = (frac + "000000").slice(0, 6);
  return BigInt(whole) * 1_000_000n + BigInt(fracPadded);
}

// EIP-2612 Permit helpers (adapted from Circle docs)
const eip2612Abi = [
  ...erc20Abi,
  {
    inputs: [{ internalType: "address", name: "owner", type: "address" }],
    stateMutability: "view",
    type: "function",
    name: "nonces",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
  },
  {
    inputs: [],
    name: "version",
    outputs: [{ internalType: "string", name: "", type: "string" }],
    stateMutability: "view",
    type: "function",
  },
];

async function eip2612Permit({ token, chain, ownerAddress, spenderAddress, value }) {
  return {
    types: {
      // Required for compatibility with Circle PW Sign Typed Data API
      EIP712Domain: [
        { name: "name", type: "string" },
        { name: "version", type: "string" },
        { name: "chainId", type: "uint256" },
        { name: "verifyingContract", type: "address" },
      ],
      Permit: [
        { name: "owner", type: "address" },
        { name: "spender", type: "address" },
        { name: "value", type: "uint256" },
        { name: "nonce", type: "uint256" },
        { name: "deadline", type: "uint256" },
      ],
    },
    primaryType: "Permit",
    domain: {
      name: await token.read.name(),
      version: await token.read.version(),
      chainId: chain.id,
      verifyingContract: token.address,
    },
    message: {
      // Convert bigint fields to string to match EIP-712 JSON schema expectations
      owner: ownerAddress,
      spender: spenderAddress,
      value: value.toString(),
      nonce: (await token.read.nonces([ownerAddress])).toString(),
      // The paymaster cannot access block.timestamp due to 4337 opcode restrictions,
      // so the deadline must be MAX_UINT256.
      deadline: maxUint256.toString(),
    },
  };
}

async function signPermit({ tokenAddress, client, account, spenderAddress, permitAmount }) {
  const token = getContract({ client, address: tokenAddress, abi: eip2612Abi });
  const permitData = await eip2612Permit({
    token,
    chain: client.chain,
    ownerAddress: account.address,
    spenderAddress,
    value: permitAmount,
  });

  const wrappedPermitSignature = await account.signTypedData(permitData);

  const isValid = await client.verifyTypedData({
    ...permitData,
    address: account.address,
    signature: wrappedPermitSignature,
  });

  if (!isValid) throw new Error(`Invalid permit signature for ${account.address}`);

  const { signature } = parseErc6492Signature(wrappedPermitSignature);
  return signature;
}

async function main() {
  const chain = baseSepolia;

  const ownerPk = normalizePk(process.env.OWNER_PRIVATE_KEY || process.env.USDC_ROUTER_PRIVATE_KEY);
  if (!ownerPk) throw new Error("Missing OWNER_PRIVATE_KEY (or USDC_ROUTER_PRIVATE_KEY)");

  const recipientAddress = getArg("--to") || process.env.RECIPIENT_ADDRESS || DEFAULTS.recipient;
  const amountStr = getArg("--amount") || DEFAULTS.amountUsdc;
  const amountUnits = parseUsdcAmount(amountStr);

  const rpcUrl = process.env.RPC_URL || DEFAULTS.rpcUrl;
  const usdcAddress = process.env.USDC_ADDRESS || DEFAULTS.usdcAddress;
  const paymasterAddress = process.env.PAYMASTER_V08_ADDRESS || DEFAULTS.paymasterV08;

  const client = createPublicClient({ chain, transport: http(rpcUrl) });
  const owner = privateKeyToAccount(ownerPk);
  const account = await toSimple7702SmartAccount({ client, owner });

  const usdc = getContract({ client, address: usdcAddress, abi: erc20Abi });
  const balanceBefore = await usdc.read.balanceOf([account.address]);

  console.log("Chain:", chain.name, `(chainId=${chain.id})`);
  console.log("Owner/Account:", account.address);
  console.log("USDC:", usdcAddress);
  console.log("Paymaster v0.8:", paymasterAddress);
  console.log("Recipient:", recipientAddress);
  console.log("USDC balance (before):", balanceBefore.toString(), "(6 decimals)");
  console.log("Transfer amount:", amountUnits.toString(), "(6 decimals)");

  if (balanceBefore < amountUnits) {
    console.log("\nInsufficient USDC. Fund this address with testnet USDC, then re-run.");
    console.log("Circle faucet: https://faucet.circle.com");
    process.exit(2);
  }

  const paymaster = {
    async getPaymasterData(_) {
      // Keep this modest; it just needs to cover the userOp + fee spread.
      const permitAmount = 10_000_000n; // 10 USDC (6 decimals)
      const permitSignature = await signPermit({
        tokenAddress: usdcAddress,
        client,
        account,
        spenderAddress: paymasterAddress,
        permitAmount,
      });

      const paymasterData = encodePacked(
        ["uint8", "address", "uint256", "bytes"],
        [0, usdcAddress, permitAmount, permitSignature],
      );

      return {
        paymaster: paymasterAddress,
        paymasterData,
        paymasterVerificationGasLimit: 200000n,
        paymasterPostOpGasLimit: 15000n,
        isFinal: true,
      };
    },
  };

  const bundlerClient = createBundlerClient({
    account,
    client,
    paymaster,
    userOperation: {
      estimateFeesPerGas: async ({ bundlerClient }) => {
        const { standard: fees } = await bundlerClient.request({
          method: "pimlico_getUserOperationGasPrice",
        });
        return {
          maxFeePerGas: hexToBigInt(fees.maxFeePerGas),
          maxPriorityFeePerGas: hexToBigInt(fees.maxPriorityFeePerGas),
        };
      },
    },
    transport: http(`https://public.pimlico.io/v2/${client.chain.id}/rpc`),
  });

  // For 7702 smart accounts, sign an authorization to set the code of the account
  // to a 7702 smart account before submitting the user operation.
  const authorization = await owner.signAuthorization({
    chainId: chain.id,
    nonce: await client.getTransactionCount({ address: owner.address }),
    contractAddress: account.authorization.address,
  });

  const userOpHash = await bundlerClient.sendUserOperation({
    account,
    calls: [
      {
        to: usdc.address,
        abi: usdc.abi,
        functionName: "transfer",
        args: [recipientAddress, amountUnits],
      },
    ],
    authorization,
  });

  console.log("\nUserOperation hash:", userOpHash);

  const receipt = await bundlerClient.waitForUserOperationReceipt({ hash: userOpHash });
  const txHash = receipt.receipt.transactionHash;
  console.log("Transaction hash:", txHash);

  // Some public RPCs can lag by a block; ensure the tx is indexed on our RPC
  // before checking balances.
  await client.waitForTransactionReceipt({ hash: txHash });

  // Some public RPC endpoints are behind load balancers; balances can lag even after
  // the receipt is visible. Poll a few times to get a consistent post-state read.
  let balanceAfter = balanceBefore;
  for (let i = 0; i < 12; i++) {
    // eslint-disable-next-line no-await-in-loop
    balanceAfter = await usdc.read.balanceOf([account.address]);
    if (balanceAfter !== balanceBefore) break;
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 1500));
  }

  console.log("USDC balance (after):", balanceAfter.toString(), "(6 decimals)");
  console.log("USDC delta:", (balanceBefore - balanceAfter).toString(), "(6 decimals)");

  process.exit(0);
}

main().catch((err) => {
  console.error("\nERROR:", err?.message || err);
  process.exit(1);
});
