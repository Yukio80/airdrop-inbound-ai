import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

class ZAIClient:
    def __init__(self):
        self.api_key = os.getenv("ZAI_API_KEY")
        self.base_url = "https://api.z.ai/api/paas/v4"

    def chat(self, prompt: str, system_prompt: str = "You are an expert Web3 airdrop strategist."):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️ z.ai API Error ({e}). Using local fallback decision engine...")
            return self._local_fallback(prompt, system_prompt)

    def _local_fallback(self, prompt: str, system_prompt: str) -> str:
        # Fallback for Strategy Generation
        if "Return ONLY JSON" in prompt or "Output only raw JSON" in system_prompt:
            return '[{"protocol": "Uniswap", "action": "swap", "amount": 0.1, "token_in": "WETH", "token_out": "USDC", "chain": "arbitrum"}]'
        
        # Fallback for Decision Making - More flexible
        import json
        try:
            # Try to extract signal data from prompt
            if "Analyze this airdrop opportunity:" in prompt:
                # Extract JSON part from prompt
                json_start = prompt.find("{")
                if json_start != -1:
                    json_part = prompt[json_start:prompt.rfind("}") + 1]
                    signal = json.loads(json_part)
                    
                    # Simple heuristic: High TVL or Arbitrum protocol = YES
                    tvl = signal.get("tvl", 0)
                    chain = signal.get("chain", "")
                    
                    if tvl > 10_000_000 or chain in ["arbitrum", "base"]:
                        return "YES. High potential based on quantitative score and chain preference. Strategy: Perform swaps and provide liquidity."
                    elif tvl > 1_000_000:
                        return "YES. Moderate potential. Strategy: Basic interactions to maintain eligibility."
        except Exception:
            pass
        
        return "NO. Low potential or insufficient data."
