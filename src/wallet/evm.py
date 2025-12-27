from .vault import SecretVault

class EvmWalletKeys:
    def __init__(self, vault: SecretVault, path="m/44'/60'/0'/0/0"):
        self._vault = vault
        self._account = None

    def load(self):
        seed = self._vault.get_seed()
        #self._account = derive_evm_account(seed)
        del seed

    @property
    def account(self):
        return self._account
