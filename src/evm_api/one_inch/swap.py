from .constants import CHAIN_ID,SWAP_BASE_URL

import requests
from requests import Response
import logging
import threading


class OneInchSwap:
    """
    Uni swap transaction generator using swap API.
    Handles CLMM and AMM automatically.
    """

    def __init__(
        self,
        chain: str,
        settings_get: callable
    ):  
        self._chain_id = CHAIN_ID.get(chain)
        self._settings_get: callable = settings_get
        self._api_key = self._settings_get("1INCH_API_KEY")
        self._lock = threading.Lock()

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("evm").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================  
    # Create transaction for signing
    # ---------------------------------------------------------
    def generate_transaction(
        self,
        input_mint: str,
        output_mint: str,
        wallet: str,
        amount_in: int,
    ) -> tuple[dict, float]:
        """
        Generate transaction for signing

        Args:
            input_mint (str): SPL token mint address
            output_mint (str): SPL token mint address
            wallet_pub_key (str): Your walet addres/public key
            amount_in (e.g. USDC = 6 decimals): amount in smallest units

        Returns:
            tuple[dict, float]:
                Transaction data and price:
                    {
                    'from': '0x89e7863bf5e38d2e46614777741545343e98db3a', 
                    'to': '0x111111125421ca6dc452d289314280a0f8842a65', 
                    'data': 'xxxxxxxxxxxx', 
                    'value': '0', 
                    'gas': 256773, 
                    'gasPrice': '43000000'
                    }
        """
        try:
            with self._lock:
                url = f"{SWAP_BASE_URL}{self._chain_id}/swap"
                body = {
                }

                heders = {
                    "Authorization": f"Bearer {self._api_key}",
                    }
                slippage = self._settings_get("evm_slippage_bps")/100
                params = {
                    "src" : input_mint,
                    "dst" : output_mint,
                    "amount" : amount_in,
                    "from" : wallet,
                    "origin" : wallet,
                    "slippage" : slippage
                }

                resp = requests.get(
                    url,
                    headers=heders,
                    json=body,
                    params=params
                    )
                resp_js = self._response_json(resp)

                recive = int(resp_js["dstAmount"])
                price = recive / amount_in
                
                return resp_js["tx"], price
                    
        except Exception as e:
            self._logger.error(f"Raydium generate_transaction() error: {e}")
            return False

    # Return price  
    # ---------------------------------------------------------
    def get_price(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: int = 1_000_000_000
    ) -> float:
        """
        Compute price after routing.

        Args:
            input_mint (str): SPL token mint address 
            output_mint (str): SPL token mint address
            amount_in (e.g. USDC = 6 decimals): amount in smallest units 

        Returns:
            float:
                Price calculated with smallest units. {in_am / out_am}
                If the decimal places of tokens are not the same you need to compute outside.
        """
        try:
            with self._lock:              

                url = f"{SWAP_BASE_URL}{self._chain_id}/quote"
                body = {
                }

                heders = {
                    "Authorization": f"Bearer {self._api_key}",
                    }

                params = {
                    "src" : input_mint,
                    "dst" : output_mint,
                    "amount" : amount_in
                }

                resp = requests.get(
                    url,
                    headers=heders,
                    json=body,
                    params=params
                    )
                resp_js = self._response_json(resp)
                if not resp_js:
                    raise RuntimeError("No data recived!")
                
                recive = int(resp_js["dstAmount"])

                price = recive / amount_in

                return price
    
        except Exception as e:
            self._logger.error(f"get_price() error: {e}")
            return False


    def approve_trx(self, mint, amount) -> dict:
        """
        Get transaction for approval

        Args:
            mint (str): token mint address 
            amount (e.g. USDC = 6 decimals): amount in smallest units 

        Returns:
            dict:
                Data from API:
                    {
                    'data': 'xxxxxxxxxxxxxxx',
                    'gasPrice': '43000000', 
                    'to': '0xaf88d065e77c8cc2239327c5edb3a432268e5831', 
                    'value': '0'
                    }
                
        """
        with self._lock:

            url = f"{SWAP_BASE_URL}{self._chain_id}/approve/transaction"

            body = {
            }   

            heders = {
                "Authorization": f"Bearer {self._api_key}",
                }
            params = {
                "tokenAddress" : mint,
                "amount" : amount,
            }

            resp = requests.get(
                url,
                headers=heders,
                json=body,
                params=params
                )
            resp_js = self._response_json(resp)
            if not resp_js:
                raise RuntimeError("No data recived!")

            return resp_js
    
    def approved_ammount(self, wallet, mint) -> int:
        """
        Get allowance ammount approved.

        Args:
            wallet (str): wallet addres.
            mint (str): token mint address 

        Returns:
            int:
                Allowance ammount in smallest units. 
        """
        with self._lock:

            url = f"{SWAP_BASE_URL}{self._chain_id}/approve/allowance"

            body = {
            }   

            heders = {
                "Authorization": f"Bearer {self._api_key}",
                }
            params = {
                "tokenAddress" : mint,
                "walletAddress" : wallet,
            }

            resp = requests.get(
                url,
                headers=heders,
                json=body,
                params=params
                )
            resp_js = self._response_json(resp)
            if not resp_js:
                raise RuntimeError("No data recived!")

            return int(resp_js["allowance"])

    # Helpers
    # ==================================================================    

    # Generate dict from response if successful
    # ---------------------------------------------------------
    @staticmethod
    def _response_json(resp: Response) -> dict:   
        if not resp.status_code == 200:
            raise ConnectionError(f"Response error status code: {resp.status_code}; response: {resp.json()}")
        resp_js = resp.json()
              
        if not resp_js.get("data"):
            raise ValueError(f"Response unsuccessful error: {resp_js["error"]}; description: {resp_js["description"]}; id: {resp_js["requestId"]}")

        return resp_js
        

    