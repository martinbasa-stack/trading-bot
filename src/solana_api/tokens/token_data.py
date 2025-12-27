import struct
import logging

from .models import TokenDataClass

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from spl.token.client import Token, MintInfo
from spl.token.constants import TOKEN_PROGRAM_ID

METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")

class TokenData:
    """
    Get token data from mint address
    """
    def __init__(
        self
    ):        
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("solana").getChild(self.__class__.__name__) 

    # Public 
    # ==================================================================  
    # Create a dict of basic token data
    # ---------------------------------------------------------
    def load_token(self, client: Client, mint_str: str) -> TokenDataClass:
        """
        Args:
            client (Client): Solana client
            mint_str (str): SPL token mint address
        Returns:
            TokenDataClass:
                Token Data:
                    {
                        "mint": mint_str,
                        "decimals": mint_info.decimals,
                        "supply": mint_info.supply,
                        "name": meta["name"],
                        "symbol": meta["symbol"],
                        "uri": meta["uri"],
                    }
        """
        try:
            mint = Pubkey.from_string(mint_str)

            token_client = Token(client, mint, TOKEN_PROGRAM_ID, None)

            mint_info: MintInfo = token_client.get_mint_info()

            meta_pda = self._metadata_pda(mint)

            meta_raw = client.get_account_info(meta_pda).value.data
            meta = self._decode_metaplex_metadata(meta_raw)

            return TokenDataClass(
                mint = mint_str,
                decimals = mint_info.decimals,
                supply = mint_info.supply,
                name = meta["name"],
                symbol = meta["symbol"],
                uri = meta["uri"],
            )
        
        except Exception as e:
            self._logger.error(f"load_token() error: {e}")
  
    # Helpers
    # ==================================================================      
    # Decoding of metadata
    # ---------------------------------------------------------
    def _decode_metaplex_metadata(self, raw: bytes):
        offset = 0

        offset += 1            # key
        offset += 32           # update authority
        offset += 32           # mint

        name, offset = self._read_string(raw, offset)
        symbol, offset = self._read_string(raw, offset)
        uri, offset = self._read_string(raw, offset)

        return {
            "name": name,
            "symbol": symbol,
            "uri": uri,
        }
    
    # Fetch meta data
    # ---------------------------------------------------------
    @staticmethod
    def _metadata_pda(mint: Pubkey) -> Pubkey:
        return Pubkey.find_program_address(
            [
                b"metadata",
                bytes(METADATA_PROGRAM_ID),
                bytes(mint),
            ],
            METADATA_PROGRAM_ID,
        )[0] 
    
    # Decode data to string
    # ---------------------------------------------------------
    @staticmethod
    def _read_string(data: bytes, offset: int):
        length = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        value = data[offset:offset + length].decode("utf-8").rstrip("\x00")
        offset += length
        return value, offset