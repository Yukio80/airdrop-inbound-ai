from solders.pubkey import Pubkey

SOLANA_RPC = "https://api.mainnet-beta.solana.com"

JUPITER_PROGRAM_ID = Pubkey.from_string("3WgzJXNB5EvEVhAoXzNvyaAGjayA9xPtaAervcEfZoST")
MARINADE_PROGRAM_ID = Pubkey.from_string("B3TmvbJawsbvhZsHhpqmTYKGbhfL78uy4rJVXoEGrfA5")

TOKEN_MINTS = {
    "SOL": Pubkey.from_string("So11111111111111111111111111111111111111112"),
    "USDC": Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    "USDT": Pubkey.from_string("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
    "mSOL": Pubkey.from_string("mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So"),
}

def get_token_mint(symbol: str) -> Pubkey:
    return TOKEN_MINTS.get(symbol.upper(), TOKEN_MINTS["SOL"])
