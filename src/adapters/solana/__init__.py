from solders.pubkey import Pubkey

SOLANA_RPC = "https://api.mainnet-beta.solana.com"

JUPITER_PROGRAM_ID = Pubkey.from_string("3WgzJXNB5EvEVhAoXzNvyaAGjayA9xPtaAervcEfZoST")
MARINADE_PROGRAM_ID = Pubkey.from_string("B3TmvbJawsbvhZsHhpqmTYKGbhfL78uy4rJVXoEGrfA5")
SANCTUM_PROGRAM_ID = Pubkey.from_string("5ocn3Kd7PJNh4o8VNMBwSYFtEdNDZhL7B2QbGApbJQco")
KAMINO_PROGRAM_ID = Pubkey.from_string("6LtLpnUFNbyqn7FHJ2J3Q8S4R7Pq3ZwBhFJ3sM2FYwnG")
METEORA_DLMM_ID = Pubkey.from_string("LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo")
METEORA_DAMM_V2_ID = Pubkey.from_string("cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG")
FRAGMETRIC_ID = Pubkey.from_string("fragnAis7Bp6FTsMoa6YcH8UffhEw43Ph79qAiK3iF3")


TOKEN_MINTS = {
    "SOL": Pubkey.from_string("So11111111111111111111111111111111111111112"),
    "USDC": Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    "USDT": Pubkey.from_string("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
    "mSOL": Pubkey.from_string("mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So"),
    "fragSOL": Pubkey.from_string("Frag6u9FAx3371HBd83fC7zsW8C9p8nNGEByK171wy4T"),
}

def get_token_mint(symbol: str) -> Pubkey:
    return TOKEN_MINTS.get(symbol.upper(), TOKEN_MINTS["SOL"])
