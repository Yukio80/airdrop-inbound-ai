#!/usr/bin/env python3
# DEPRECATED — use src/bridge/lifi_bridge.py instead
"""
Swap ETH (BEP-20) → USDT no PancakeSwap,
depois bridge USDT BSC → USDT Arbitrum via Stargate.
"""
import json, sys, time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account.account import Account

ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"
BSC_RPC = "https://bsc-dataseed.binance.org"
ARB_RPC = "https://arb1.arbitrum.io/rpc"
CHAIN_ID = 56

PCS_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
STARGATE_ROUTER = "0x4a364f8c717cAAD9A442737Eb7b8A55cc6cf18D8"
ETH = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
USDT = "0x55d398326f99059fF775485246999027B3197955"
USDT_ARB = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"

SG_USDT_POOL = 2
ARB_CHAIN_ID = 110
LZ_DST = bytes.fromhex(ADDR[2:].lower())

PK = None
NONCE = None

ERC20 = json.loads('''[
{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"name":"","type":"bool"}],"type":"function"}
]''')

SG_ABI = json.loads('''[
{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint256","name":"_srcPoolId","type":"uint256"},{"internalType":"uint256","name":"_dstPoolId","type":"uint256"},{"internalType":"address payable","name":"_refundAddress","type":"address"},{"internalType":"uint256","name":"_amountLD","type":"uint256"},{"internalType":"uint256","name":"_minAmountLD","type":"uint256"},{"components":[{"internalType":"uint256","name":"dstGasForCall","type":"uint256"},{"internalType":"uint256","name":"dstNativeAmount","type":"uint256"},{"internalType":"bytes","name":"dstNativeAddr","type":"bytes"}],"internalType":"struct Router.lzTxObj","name":"_lzTxParams","type":"tuple"},{"internalType":"bytes","name":"_to","type":"bytes"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"swap","outputs":[],"stateMutability":"payable","type":"function"},
{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint8","name":"_functionType","type":"uint8"},{"internalType":"bytes","name":"_toAddress","type":"bytes"},{"internalType":"bytes","name":"_transferAndCallPayload","type":"bytes"},{"components":[{"internalType":"uint256","name":"dstGasForCall","type":"uint256"},{"internalType":"uint256","name":"dstNativeAmount","type":"uint256"},{"internalType":"bytes","name":"dstNativeAddr","type":"bytes"}],"internalType":"struct Router.lzTxObj","name":"_lzTxParams","type":"tuple"}],"name":"quoteLayerZeroFee","outputs":[{"internalType":"uint256","name":"nativeFee","type":"uint256"},{"internalType":"uint256","name":"zroFee","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

PCS_ABI = json.loads('''[
{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}
]''')

def send_tx(w3, tx, pk):
    tx["nonce"] = w3.eth.get_transaction_count(Web3.to_checksum_address(ADDR))
    if "gasPrice" not in tx and "maxFeePerGas" not in tx:
        tx["gasPrice"] = w3.eth.gas_price
    elif "gasPrice" in tx:
        pass
    signed = w3.eth.account.sign_transaction(tx, pk)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    hex_h = w3.to_hex(h)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    return hex_h, r["status"]

def main():
    global PK
    print("=" * 55)
    print("🔄 Swap ETH → USDT (PancakeSwap) + Bridge (Stargate)")
    print("=" * 55)

    with open("wallets/user_real.json") as f:
        ks = json.load(f)
    PK = Account.decrypt(ks, "231413")

    w3 = Web3(Web3.HTTPProvider(BSC_RPC, request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    w3a = Web3(Web3.HTTPProvider(ARB_RPC, request_kwargs={"timeout": 15}))
    acct = Web3.to_checksum_address(ADDR)

    eth_t = w3.eth.contract(address=Web3.to_checksum_address(ETH), abi=ERC20)
    usdt_t = w3.eth.contract(address=Web3.to_checksum_address(USDT), abi=ERC20)
    pcs = w3.eth.contract(address=Web3.to_checksum_address(PCS_ROUTER), abi=PCS_ABI)
    sg = w3.eth.contract(address=Web3.to_checksum_address(STARGATE_ROUTER), abi=SG_ABI)

    # ── Balances ──
    bnb = w3.eth.get_balance(acct) / 1e18
    eth_bal = eth_t.functions.balanceOf(acct).call()
    eth_bal_dec = eth_bal / 1e18
    print(f"\n📊 BSC:")
    print(f"   BNB:  {bnb:.6f}")
    print(f"   ETH:  {eth_bal_dec:.6f} (~${eth_bal_dec*3500:.2f})")

    if eth_bal < 1000:
        print("❌ ETH insuficiente"); sys.exit(1)

    # ── Step 1: Swap ETH → USDT on PancakeSwap ──
    print(f"\n{'─'*50}")
    print("1️⃣  Swap ETH → USDT no PancakeSwap")
    print(f"{'─'*50}")

    path = [Web3.to_checksum_address(ETH), Web3.to_checksum_address(WBNB), Web3.to_checksum_address(USDT)]
    amounts_out = pcs.functions.getAmountsOut(eth_bal, path).call()
    expected_usdt = amounts_out[-1]
    print(f"   Previsão: {eth_bal_dec:.6f} ETH → {expected_usdt / 1e18:.2f} USDT")

    allowance = eth_t.functions.allowance(acct, Web3.to_checksum_address(PCS_ROUTER)).call()
    if allowance < eth_bal:
        print(f"\n📝 Approve ETH → PancakeSwap Router...")
        tx_h, status = send_tx(w3, eth_t.functions.approve(
            Web3.to_checksum_address(PCS_ROUTER), eth_bal
        ).build_transaction({"from": acct, "gas": 60000}), PK)
        print(f"   Approve: {tx_h}")
        print(f"   {'✅' if status else '❌'}")

    min_out = int(expected_usdt * 0.99)  # 1% slippage
    deadline = int(time.time()) + 600
    tx_h, status = send_tx(w3, pcs.functions.swapExactTokensForTokens(
        eth_bal, min_out, path, acct, deadline
    ).build_transaction({"from": acct, "gas": 300000}), PK)

    print(f"   Swap: {tx_h}")
    if status != 1:
        print("   ❌ Swap falhou!"); sys.exit(1)
    print("   ✅ Swap concluído!")

    # Check USDT received
    usdt_received = usdt_t.functions.balanceOf(acct).call()
    usdt_dec = usdt_received / 1e18
    print(f"   📥 Recebido: {usdt_dec:.2f} USDT")

    if usdt_received < 100:
        print("   ❌ USDT insuficiente após swap"); sys.exit(1)

    # ── Step 2: Bridge USDT → Arbitrum via Stargate ──
    print(f"\n{'─'*50}")
    print("2️⃣  Bridge USDT BSC → USDT Arbitrum via Stargate")
    print(f"{'─'*50}")

    lz_tx = (0, 0, b"")
    fee_native, _ = sg.functions.quoteLayerZeroFee(
        ARB_CHAIN_ID, 1, LZ_DST, b"", lz_tx
    ).call()
    fee_bnb = fee_native / 1e18
    print(f"   LayerZero fee: {fee_bnb:.6f} BNB")

    if w3.eth.get_balance(acct) / 1e18 < fee_bnb + 0.00005:
        print("   ❌ BNB insuficiente para taxa"); sys.exit(1)

    allowance_usdt = usdt_t.functions.allowance(acct, Web3.to_checksum_address(STARGATE_ROUTER)).call()
    if allowance_usdt < usdt_received:
        print(f"\n📝 Approve USDT → Stargate Router...")
        tx_h, status = send_tx(w3, usdt_t.functions.approve(
            Web3.to_checksum_address(STARGATE_ROUTER), usdt_received
        ).build_transaction({"from": acct, "gas": 60000}), PK)
        print(f"   Approve: {tx_h}")
        print(f"   {'✅' if status else '❌'}")

    min_usdt = int(usdt_received * 0.995)
    print(f"\n🚀 Bridging {usdt_dec:.2f} USDT → Arbitrum...")

    tx_h, status = send_tx(w3, sg.functions.swap(
        ARB_CHAIN_ID, SG_USDT_POOL, SG_USDT_POOL,
        acct, usdt_received, min_usdt,
        lz_tx, LZ_DST, b""
    ).build_transaction({"from": acct, "gas": 400000, "value": fee_native}), PK)

    print(f"   Bridge: {tx_h}")
    print(f"   🔗 https://bscscan.com/tx/{tx_h}")
    if status != 1:
        print("   ❌ Bridge falhou!"); sys.exit(1)
    print("   ✅ Bridge submetida! ⏳ ~5-15 min para chegar no Arbitrum")

    # ── Wait for arrival ──
    print(f"\n⏱ Aguardando fundos no Arbitrum...")
    usdt_arb = w3a.eth.contract(address=Web3.to_checksum_address(USDT_ARB), abi=ERC20)
    for i in range(40):
        time.sleep(15)
        arb_eth = w3a.eth.get_balance(acct) / 1e18
        arb_usdt = usdt_arb.functions.balanceOf(acct).call() / 1e18
        print(f"   [{i+1}/40] ETH: {arb_eth:.8f} | USDT: {arb_usdt:.6f}")
        if arb_usdt > 0.01:
            print(f"\n🎉 USDT CHEGOU no Arbitrum! {arb_usdt:.2f} USDT")
            print(f"   Saldo ETH no Arbitrum: {arb_eth:.8f}")
            print(f"   ✅ Pronto para executar interações reais no Arbitrum!")
            return

    print("\n⚠️ Ainda não chegou. Verifique o explorador:")
    print(f"   https://stargate-explorer.layerzero.network/tx/{tx_h}")

if __name__ == "__main__":
    main()
