from .vault import SecretVault
from .utils import load_json
from .solana import SolanaWalletKeys


from src.constants import FILE_PATH_WALLET

encrypted_blob = load_json(FILE_PATH_WALLET)

vault_obj = SecretVault(encrypted_blob)

solana_wallet = SolanaWalletKeys(vault_obj)

def reload_wallet() -> SecretVault:
    encrypted_blob = load_json(FILE_PATH_WALLET)
    vault_obj.reload(encrypted_blob)
    return vault_obj
