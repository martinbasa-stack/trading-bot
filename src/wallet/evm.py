from .vault import SecretVault

from eth_account import Account
import bip32utils
from eth_keys import keys
from eth_utils import to_checksum_address

BIP44_HARDEN = bip32utils.BIP32_HARDEN


class EvmWalletKeys:
    def __init__(self, vault: SecretVault, path="m/44'/60'/0'/0/0"):
        self._vault = vault
        self._address = None
        self._account = None


    @property
    def account(self) -> Account:
        return self._account
    
    @property
    def pub_address(self) -> str:
        return self._address

    def load(self):
        seed = self._vault.get_seed()        
        priv_hex = self._derive_evm_account(seed)
        self._account = Account.from_key(priv_hex)
        del seed, priv_hex

    def _derive_evm_account(self, seed: bytes, index: int = 0) -> str:
        """
        Derive EVM private key + address from seed.

        Path: m/44'/60'/0'/0/{index}
        """
        root = bip32utils.BIP32Key.fromEntropy(seed)

        child = (
            root
            .ChildKey(44 + BIP44_HARDEN)
            .ChildKey(60 + BIP44_HARDEN)
            .ChildKey(0 + BIP44_HARDEN)
            .ChildKey(0)
            .ChildKey(index)
        )

        priv_key = keys.PrivateKey(child.PrivateKey())
        self._address = to_checksum_address(priv_key.public_key.to_address())

        return priv_key.to_hex()


