import struct
import logging

from .models import TokenDataClass, ERC20_ABI

from web3 import Web3

class EvmTokenData:
    """
    Get token data from mint address
    """
    def __init__(
        self
    ):
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("evm").getChild(self.__class__.__name__) 

    # Public 
    # ==================================================================  
    def load_token(self, web3: Web3, mint_str: str) -> TokenDataClass | None:
        """
        Args:
            web3 (Web3): Web3 EVM client
            mint_str (str): ERC20 token contract address
        Returns:
            TokenDataClass | None
        """
        try:
            address = Web3.to_checksum_address(mint_str)

            contract = web3.eth.contract(
                address=address,
                abi=ERC20_ABI
            )

            decimals = contract.functions.decimals().call()
            supply = contract.functions.totalSupply().call()
            name = self._safe_string_call(contract.functions.name)
            symbol = self._safe_string_call(contract.functions.symbol)

            return TokenDataClass(
                mint=address,
                decimals=decimals,
                supply=supply,
                name=name,
                symbol=symbol,
                uri=None,   # Not standard on ERC-20
            )

        except Exception as e:
            self._logger.error(f"load_token() error: {e}")
            return None
  
    # Helpers
    # ==================================================================      
    def _safe_string_call(self, fn):
        try:
            value = fn().call()

            if isinstance(value, bytes):
                return value.rstrip(b"\x00").decode("utf-8")

            return value

        except Exception:
            return None

    