"""
Arbitrum Real — executa transações reais na Arbitrum.
Swap ETH→USDC na Uniswap V3 + Supply USDC no Aave V3.
Usa o saldo real: 0.000217 ETH + keystore user_real.json.
"""
import json, time, sys
from pathlib import Path
from web3 import Web3
from eth_account import Account

ROOT = Path(__file__).parent.parent
KEYSTORE = ROOT / "wallets" / "user_real.json"
PASSWORD = "231413"
ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

RPC = "https://arb1.arbitrum.io/rpc"

# --- Contract Addresses (Arbitrum) ---
SUSHI_ROUTER = Web3.to_checksum_address("0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506")
WETH = Web3.to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
USDC = Web3.to_checksum_address("0xaf88D065E77c8cC2239327a0744Cea99E457DC4b")
USDC_E = Web3.to_checksum_address("0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8")
AAVE_POOL = Web3.to_checksum_address("0x794a61358D6845594F94dc1DB02A252b5b4814aD")

# --- ABIs ---
SUSHI_ROUTER_ABI = json.loads('''[{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"}]''')

AAVE_POOL_ABI = json.loads('''[{"inputs":[{"name":"asset","type":"address"},{"name":"amount","type":"uint256"},{"name":"onBehalfOf","type":"address"},{"name":"referralCode","type":"uint16"}],"name":"supply","outputs":[],"stateMutability":"nonpayable","type":"function"}]''')

ERC20_ABI = json.loads('''[{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"}]''')

RECIPIENT = Web3.to_checksum_address(ADDR)

def load_wallet():
    with open(KEYSTORE) as f:
        ks = json.load(f)
    pk = Account.decrypt(ks, PASSWORD)
    return Account.from_key(pk)

def estimate_gas(w3, tx):
    try:
        return w3.eth.estimate_gas(tx)
    except Exception as e:
        print(f"   ⚠️  Gas estimate failed: {str(e)[:80]}")
        return None

def send_tx(w3, tx, wallet):
    signed = w3.eth.account.sign_transaction(tx, wallet.key)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"   Tx enviada: {w3.to_hex(h)}")
    print(f"   https://arbiscan.io/tx/{w3.to_hex(h)}")
    receipt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    status = "✅" if receipt["status"] == 1 else "❌"
    gas_used = receipt["gasUsed"]
    print(f"   {status} Confirmada (gas: {gas_used}, block: {receipt['blockNumber']})")
    return w3.to_hex(h), receipt

def get_gas_params(w3):
    block = w3.eth.get_block("latest")
    base_fee = block.get("baseFeePerGas", 0)
    try:
        max_priority = w3.eth.max_priority_fee
        if not max_priority:
            max_priority = 100000000
    except:
        max_priority = 100000000
    max_fee = int((base_fee + max_priority) * 1.5)
    return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_priority}

def step1_swap_eth_to_usdc(w3, wallet, amount_eth):
    print(f"\n{'='*50}")
    print(f"Passo 1: Swap {amount_eth:.8f} ETH → USDC.e no SushiSwap")
    print(f"{'='*50}")
    
    router = w3.eth.contract(address=SUSHI_ROUTER, abi=SUSHI_ROUTER_ABI)
    amount_in = w3.to_wei(amount_eth, "ether")
    path = [WETH, USDC_E]
    deadline = w3.eth.get_block("latest")["timestamp"] + 600
    
    tx = router.functions.swapExactETHForTokens(
        1, path, RECIPIENT, deadline
    ).build_transaction({
        "from": RECIPIENT,
        "value": amount_in,
        "nonce": w3.eth.get_transaction_count(RECIPIENT),
        **get_gas_params(w3),
    })
    
    gas = estimate_gas(w3, tx)
    if gas:
        tx["gas"] = gas
    else:
        tx["gas"] = 250000
    
    total_cost = tx.get("gasPrice", 0) * tx.get("gas", 0) + amount_in
    cost_eth = total_cost / 1e18
    eth_bal = w3.eth.get_balance(RECIPIENT) / 1e18
    print(f"   ETH bal: {eth_bal:.8f}, custo total: {cost_eth:.8f} ETH")
    
    if cost_eth > eth_bal:
        print(f"   ❌ Saldo insuficiente")
        return None
    
    return send_tx(w3, tx, wallet)

def step2_approve_usdc(w3, wallet, amount_usdc):
    print(f"\n{'='*50}")
    print(f"Passo 2: Approve USDC para o Aave Pool")
    print(f"{'='*50}")
    
    usdc_contract = w3.eth.contract(address=USDC_E, abi=ERC20_ABI)
    amount = int(amount_usdc * 1e6)
    
    tx = usdc_contract.functions.approve(AAVE_POOL, amount).build_transaction({
        "from": RECIPIENT,
        "nonce": w3.eth.get_transaction_count(RECIPIENT),
        **get_gas_params(w3),
    })
    
    gas = estimate_gas(w3, tx)
    tx["gas"] = gas if gas else 50000
    
    cost = tx["maxFeePerGas"] * tx["gas"] / 1e18
    eth_bal = w3.eth.get_balance(RECIPIENT) / 1e18
    print(f"   ETH bal: {eth_bal:.8f}, gas cost: {cost:.8f}")
    
    if cost > eth_bal:
        print(f"   ❌ Saldo insuficiente")
        return None
    
    return send_tx(w3, tx, wallet)

def step3_supply_usdc(w3, wallet, amount_usdc):
    print(f"\n{'='*50}")
    print(f"Passo 3: Supply USDC no Aave V3")
    print(f"{'='*50}")
    
    pool = w3.eth.contract(address=AAVE_POOL, abi=AAVE_POOL_ABI)
    amount = int(amount_usdc * 1e6)
    supply_token = USDC_E  # USDC.e tem pools Aave
    
    tx = pool.functions.supply(supply_token, amount, RECIPIENT, 0).build_transaction({
        "from": RECIPIENT,
        "nonce": w3.eth.get_transaction_count(RECIPIENT),
        **get_gas_params(w3),
    })
    
    gas = estimate_gas(w3, tx)
    tx["gas"] = gas if gas else 300000
    
    cost = tx["maxFeePerGas"] * tx["gas"] / 1e18
    eth_bal = w3.eth.get_balance(RECIPIENT) / 1e18
    print(f"   ETH bal: {eth_bal:.8f}, gas cost: {cost:.8f}")
    
    if cost > eth_bal:
        print(f"   ❌ Saldo insuficiente")
        return None
    
    return send_tx(w3, tx, wallet)

def check_balances(w3):
    eth = w3.eth.get_balance(RECIPIENT) / 1e18
    
    def get_bal(token, name):
        try:
            data = "0x70a08231" + RECIPIENT[2:].rjust(64, "0")
            result = w3.eth.call({"to": token, "data": data})
            if result and result.hex() != "0x" * 33:
                return int(result.hex(), 16) / 1e6
        except:
            pass
        return 0
    
    usdc_e = get_bal(USDC_E, "USDC.e")
    usdc = get_bal(USDC, "USDC")
    
    print(f"\n📊 Balances atuais:")
    print(f"   ETH:    {eth:.8f}")
    print(f"   USDC.e: {usdc_e:.6f}")
    print(f"   USDC:   {usdc:.6f}")
    return eth, usdc_e + usdc

def main():
    print("=" * 50)
    print("🚀 Arbitrum Real — Transações On-Chain")
    print("=" * 50)
    
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print("❌ RPC não conectado")
        return
    
    print(f"\nRede: Arbitrum One (chain ID: {w3.eth.chain_id})")
    print(f"Wallet: {ADDR}")
    
    wallet = load_wallet()
    print(f"Wallet loaded: {wallet.address}")
    
    eth_bal, usdc_bal = check_balances(w3)
    
    if usdc_bal <= 0 and eth_bal > 0.0001:
        swap_amount = eth_bal * 0.5
        result = step1_swap_eth_to_usdc(w3, wallet, swap_amount)
        if result:
            _, receipt = result
            if receipt["status"] == 1:
                time.sleep(2)
                eth_bal, usdc_bal = check_balances(w3)
    
    if usdc_bal > 0:
        result = step2_approve_usdc(w3, wallet, usdc_bal)
        if result:
            _, receipt = result
            if receipt["status"] == 1:
                time.sleep(2)
                result = step3_supply_usdc(w3, wallet, usdc_bal)
                if result:
                    print(f"\n✅ Ciclo completo: swap + approve + supply executados!")
    
    print(f"\n📊 Balances finais:")
    check_balances(w3)

if __name__ == "__main__":
    main()
