
from solders.keypair import Keypair

from .vault import SecretVault

class SolanaWalletKeys:
    def __init__(self, vault : SecretVault , derivation_path="m/44'/501'/0'/0'"):
        self._derivation_path = derivation_path
        self._vault = vault
        self._keypair = None
        self._pub_key = None

    def load(self):
        seed = self._vault.get_seed()
        self._keypair = Keypair.from_seed_and_derivation_path(seed, self._derivation_path)
        self._pub_key =  self._keypair.pubkey()
        del seed

    @property
    def keypair(self):
        return self._keypair
    
    @property
    def pub_key(self):
        return self._pub_key
