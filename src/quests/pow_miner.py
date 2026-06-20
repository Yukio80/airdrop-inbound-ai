"""
PoW Faucet Miner for Sepolia/Holesky testnet ETH.
No mainnet balance required — mines using secp256k1 recovery as proof-of-work.
"""
import json, time, os, random, sys, struct, hashlib
import threading
from eth_hash.auto import keccak
from eth_keys.datatypes import Signature

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

WALLET = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

FAUCETS = {
    "sepolia": {
        "base": "https://sepolia-faucet.pk910.de",
        "ws_base": "wss://sepolia-faucet.pk910.de",
    },
    "hoodi": {
        "base": "https://hoodi-faucet.pk910.de",
        "ws_base": "wss://hoodi-faucet.pk910.de",
    },
}

def get_create_addr(deployer_hash):
    addr_bytes = bytearray(20)
    addr_bytes[0] = 0xd6
    addr_bytes[1] = 0x94
    addr_bytes[2:22] = deployer_hash[:20]
    addr_bytes[22] = 0x80
    h = keccak(bytes(addr_bytes))
    return h[12:32]

def miner_run(nonce_int, input_hash, input_sig_r, input_sig_v, preimage_hash, max_rounds, output_suffix, output_prefix, suffix_len, prefix_len):
    best_score = 0
    best_addr = None
    best_nonce = None
    
    sig_v = input_sig_v - 27
    
    nonce_base = struct.pack('>Q', nonce_int)[:8]
    
    for i in range(max_rounds):
        nonce_bytes = nonce_base + preimage_hash[:8]
        nonce_bytes += bytes([(i >> 8) & 0xff, i & 0xff])
        
        s_bytes = nonce_bytes.rjust(32, b'\x00')
        
        try:
            sig = Signature(signature_bytes=bytes([sig_v]) + input_sig_r + s_bytes)
            pk = sig.recover_public_key_from_msg_hash(input_hash)
            ser = pk.to_bytes()
        except Exception:
            continue
        
        if len(ser) != 65 or ser[0] != 4:
            continue
        
        pubkey_hash = keccak(ser[1:65])
        addr = get_create_addr(pubkey_hash[12:32])
        
        score = 0
        for j in range(suffix_len):
            diff = addr[19 - j] ^ output_suffix[suffix_len - 1 - j]
            if diff & 0x01: break; score += 1
            if diff & 0x02: break; score += 1
            if diff & 0x04: break; score += 1
            if diff & 0x08: break; score += 1
            if diff & 0x10: break; score += 1
            if diff & 0x20: break; score += 1
            if diff & 0x40: break; score += 1
            if diff & 0x80: break; score += 1
        
        if score == suffix_len * 8:
            for j in range(prefix_len):
                diff = addr[j] ^ output_prefix[j]
                if diff & 0x80: break; score += 1
                if diff & 0x40: break; score += 1
                if diff & 0x20: break; score += 1
                if diff & 0x10: break; score += 1
                if diff & 0x08: break; score += 1
                if diff & 0x04: break; score += 1
                if diff & 0x02: break; score += 1
                if diff & 0x01: break; score += 1
        
        if score > best_score:
            best_score = score
            best_addr = addr
            best_nonce = nonce_bytes
    
    data = f"0x{best_score:02x}"
    for b in best_addr:
        data += f"{b:02x}"
    for b in best_nonce:
        data += f"{b:02x}"
    return data, best_score

class PoWFaucetMiner:
    def __init__(self, network="sepolia", wallet=WALLET):
        self.network = network
        self.wallet = wallet
        cfg = FAUCETS[network]
        self.base_url = cfg["base"]
        self.ws_url = cfg["ws_base"]
        
        self.input_hash = None
        self.input_sig_r = None
        self.input_sig_v = None
        self.preimage_hash = None
        self.output_suffix = None
        self.output_prefix = None
        self.suffix_len = 0
        self.prefix_len = 0
        self.max_rounds = 0
        self.difficulty = 0
        self.pow_params_str = None
        self.params_hash = None
        self.session_id = None
        
        self.balance = 0
        self.nonce = 0
        self.running = False
    
    def get_faucet_config(self):
        r = requests.get(f"{self.base_url}/api/getFaucetConfig", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        return r.json()
    
    def start_session(self):
        r = requests.post(f"{self.base_url}/api/startSession",
                          json={"target": self.wallet},
                          timeout=15,
                          headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        return r.json()
    
    def init_from_config(self):
        cfg = self.get_faucet_config()
        pow_cfg = cfg.get("modules", {}).get("pow", {})
        params = pow_cfg.get("powParams", {})
        
        self.difficulty = pow_cfg.get("powDifficulty", 13)
        self.pow_params_str = json.dumps(params)
        self.params_hash = hashlib.sha256(self.pow_params_str.encode()).hexdigest()
        
        self.input_hash = bytes.fromhex(params["i"])
        self.input_sig_r = bytes.fromhex(params["r"])
        self.input_sig_v = params["v"]
        self.max_rounds = params["c"]
        
        suffix = bytes.fromhex(params["s"])
        self.output_suffix = suffix
        self.suffix_len = len(suffix)
        
        prefix = bytes.fromhex(params["p"])
        self.output_prefix = prefix
        self.prefix_len = len(prefix)
        
        return pow_cfg
    
    async def mine(self):
        print(f"⚡ PoW Miner — {self.network.upper()}")
        print(f"   Wallet: {self.wallet}")
        print(f"   Difficulty: {self.difficulty} bits")
        print()
        
        pow_cfg = self.init_from_config()
        print(f"   Algo: nickminer, rounds: {self.max_rounds}")
        print(f"   Suffix: {self.output_suffix.hex()}, Prefix: {self.output_prefix.hex()}")
        print()
        
        session = self.start_session()
        if session.get("status") == "failed":
            print(f"❌ Session failed: {session.get('failedReason')}")
            return False
        
        self.session_id = session.get("session")
        preimage = session.get("preImage", session.get("data", {}).get("pow", {}).get("preImage"))
        
        if not preimage:
            print(f"Session response: {json.dumps(session, indent=2)[:500]}")
            print("❌ Could not find preimage in session response")
            return False
        
        print(f"   Session: {self.session_id}")
        print(f"   Preimage: {preimage}")
        
        preimage_bytes = bytes.fromhex(preimage) if len(preimage) == 64 else bytes.fromhex(preimage[2:] if preimage.startswith("0x") else preimage)
        self.preimage_hash = keccak(preimage_bytes)
        
        print(f"   Preimage hash: {self.preimage_hash.hex()}")
        print()
        
        ws_url = f"{self.ws_url}/ws/pow?session={self.session_id}"
        
        async with websockets.connect(ws_url, ping_interval=30) as ws:
            self.running = True
            print("✅ WebSocket connected, mining...")
            print()
            
            shares_found = 0
            start_time = time.time()
            last_report = start_time
            
            while self.running:
                nonce = self.nonce
                self.nonce += 1
                
                data, score = miner_run(
                    nonce, self.input_hash, self.input_sig_r, self.input_sig_v,
                    self.preimage_hash, self.max_rounds,
                    self.output_suffix, self.output_prefix,
                    self.suffix_len, self.prefix_len
                )
                
                elapsed = time.time() - last_report
                if elapsed >= 10:
                    rate = self.nonce / (time.time() - start_time)
                    print(f"   ⛏️  Nonce {nonce} (score: {score}/{self.difficulty}, rate: {rate:.1f}/s)")
                    last_report = time.time()
                
                if score >= self.difficulty:
                    msg = {
                        "action": "foundShare",
                        "data": {
                            "nonce": nonce,
                            "data": data,
                            "params": self.params_hash,
                            "hashrate": 0,
                        },
                        "id": nonce,
                    }
                    await ws.send(json.dumps(msg))
                    shares_found += 1
                    print(f"   ✅ Share #{shares_found} submitted! (score: {score})")
                    
                    response = await ws.recv()
                    resp = json.loads(response)
                    if resp.get("action") == "ok":
                        print(f"      ✓ Accepted")
                    elif resp.get("action") == "error":
                        print(f"      ✗ Rejected: {resp.get('data', {}).get('message', '')}")
                
                if shares_found >= 10:
                    print(f"   ✅ 10 shares found, claiming reward...")
                    break
            
            if shares_found > 0:
                await ws.send(json.dumps({"action": "closeSession", "id": 999}))
                response = await ws.recv()
                print(f"   Session closed: {response[:200]}")
                
                r = requests.post(f"{self.base_url}/api/claimReward",
                                  json={"session": self.session_id},
                                  timeout=15,
                                  headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
                result = r.json()
                print(f"   Claim result: {json.dumps(result, indent=2)}")
        
        return True

async def main():
    import asyncio
    network = sys.argv[1] if len(sys.argv) > 1 else "sepolia"
    if network not in FAUCETS:
        print(f"Networks: {', '.join(FAUCETS.keys())}")
        return
    
    miner = PoWFaucetMiner(network)
    await miner.mine()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
