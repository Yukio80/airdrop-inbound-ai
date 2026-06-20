#!/usr/bin/env python3
# DEPRECATED — use src/bridge/lifi_bridge.py instead
"""
Bridge BNB (BSC) → ETH (Arbitrum) via LI.FI API + NearIntents.
"""
import json, sys, time, requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account.account import Account

ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"
BSC_RPC = "https://bsc-dataseed.binance.org"
LIFI_URL = "https://li.quest/v1/quote"

w3 = Web3(Web3.HTTPProvider(BSC_RPC, request_kwargs={"timeout": 15}))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
acct = Web3.to_checksum_address(ADDR)

with open("wallets/user_real.json") as f:
    ks = json.load(f)
PK = Account.decrypt(ks, "231413")

bnb_balance = w3.eth.get_balance(acct)
bnb_dec = bnb_balance / 1e18
print(f"📊 BSC: {bnb_dec:.8f} BNB")
print(f"   Endereço: {acct}")

# Decrease by gas margin: send 0.00063 out of 0.000691
# Gas needed: ~70000 gas * 50gwei = 0.0000035 BNB, use 0.000005 margin
# Extra buffer: keep 0.00004 BNB for safety
gas_buf = 5000000000000  # 0.000005 BNB
extra = 40000000000000   # 0.00004 BNB
send_amount = bnb_balance - extra
if send_amount <= 0:
    print("❌ BNB insuficiente"); sys.exit(1)

print(f"   Enviando: {send_amount/1e18:.8f} BNB")
print(f"   Reserva:  {extra/1e18:.8f} BNB")

print("\n🔄 Solicitando rota BNB→ETH(Arbitrum) via LI.FI...")
params = {
    "fromChain": "BSC", "toChain": "ARB",
    "fromToken": "BNB", "toToken": "ETH",
    "fromAmount": str(send_amount),
    "fromAddress": ADDR,
    "toAddress": ADDR,
    "slippage": 0.5,
    "integrator": "opencode",
}
r = requests.get(LIFI_URL, params=params, timeout=30)
data = r.json()

if "transactionRequest" not in data:
    print(f"❌ LI.FI erro: {data.get('message', data)}")
    sys.exit(1)

tx_req = data["transactionRequest"]
to_amount = int(data["estimate"]["toAmount"])
to_dec = to_amount / 1e18
print(f"   ✅ Receberá ~{to_dec:.8f} ETH (~${to_dec*1725:.4f})")
print(f"   ⏱ ~{data['estimate'].get('executionDuration', '?')}s")

tx = {
    "to": Web3.to_checksum_address(tx_req["to"]),
    "from": acct,
    "value": int(tx_req["value"], 16),
    "data": tx_req["data"],
    "gas": int(tx_req.get("gasLimit", "0xb48ac"), 16),
    "gasPrice": w3.eth.gas_price,
    "nonce": w3.eth.get_transaction_count(acct),
}
cost = tx["value"] + tx["gas"] * tx["gasPrice"]
print(f"\n📋 Tx: value={tx['value']/1e18:.8f}, gas={tx['gas']}, gwei={tx['gasPrice']/1e9}")
print(f"   Custo total: {cost/1e18:.8f} BNB")
print(f"   Saldo:       {bnb_balance/1e18:.8f} BNB")
if cost > bnb_balance:
    print(f"   ❌ Faltam {(cost-bnb_balance)/1e18:.8f} BNB")
    # Retry with lower amount
    deficit = cost - bnb_balance
    new_send = send_amount - deficit - gas_buf
    print(f"   Tentando com {new_send/1e18:.8f} BNB...")
    params["fromAmount"] = str(new_send)
    r = requests.get(LIFI_URL, params=params, timeout=30)
    data = r.json()
    if "transactionRequest" not in data:
        print(f"❌ LI.FI erro retry: {data.get('message', data)}")
        sys.exit(1)
    tx_req = data["transactionRequest"]
    tx = {
        "to": Web3.to_checksum_address(tx_req["to"]),
        "from": acct,
        "value": int(tx_req["value"], 16),
        "data": tx_req["data"],
        "gas": int(tx_req.get("gasLimit", "0xb48ac"), 16),
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(acct),
    }
    to_amount = int(data["estimate"]["toAmount"])
    to_dec = to_amount / 1e18
    print(f"   ✅ Nova rota: receberá ~{to_dec:.8f} ETH")

print(f"\n🚀 Enviando tx bridge...")
signed = w3.eth.account.sign_transaction(tx, PK)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
hex_h = w3.to_hex(h)
print(f"   Tx: {hex_h}")
print(f"   🔗 https://bscscan.com/tx/{hex_h}")

receipt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
if receipt["status"] != 1:
    print(f"❌ Tx falhou! gasUsed={receipt['gasUsed']}")
    sys.exit(1)
print("✅ Bridge submetida com sucesso!")

print(f"\n⏱ Aguardando ETH chegar na Arbitrum...")
arb_w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))
for i in range(60):
    time.sleep(10)
    eth = arb_w3.eth.get_balance(acct) / 1e18
    print(f"   [{i+1}/60] ETH: {eth:.8f}")
    if eth > 0.0001:
        print(f"\n🎉 ETH CHEGOU na Arbitrum! {eth:.8f} ETH")
        with open("logs/bridge_bnb_to_arb.log", "w") as f:
            f.write(f"tx: {hex_h}\neth: {eth}\nts: {time.time()}\n")
        sys.exit(0)

print("\n⚠️ Ainda não chegou. Verifique:")
print(f"   https://bscscan.com/tx/{hex_h}")
