# Circle CCTP Forwarding Service (notes)

Primary reference (Base Sepolia → Avalanche Fuji example):
- https://developers.circle.com/cctp/howtos/transfer-usdc-with-forwarding-service

Key constants from Circle docs:
- Base Sepolia USDC: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- Base Sepolia TokenMessengerV2: `0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA`
- Base Sepolia domain: `6`
- Avalanche Fuji domain: `1`

Forwarding hookData (static):
```
0x636374702d666f72776172640000000000000000000000000000000000000000
```

Fees endpoint (no auth needed):
- `https://iris-api-sandbox.circle.com/v2/burn/USDC/fees/6/1?forward=true`

Message status endpoint (poll for forwardTxHash):
- `https://iris-api-sandbox.circle.com/v2/messages/6?transactionHash=<burnTxHash>`
