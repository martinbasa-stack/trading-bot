from .constants import QUOTE_API_URL, TRX_API_URL, DATA_BASE_URL

import requests
from requests import Response
import logging
import threading

from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address


class RaydiumSwap:
    """
    Raydium swap transaction generator using Raydium v3 swap API.
    Handles CLMM and AMM automatically.
    """

    def __init__(
        self,
        settings_get: callable
    ):  
        self._settings_get = settings_get      
        self._lock = threading.Lock()

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("solana").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================  
    # Create transaction for signing
    # ---------------------------------------------------------
    def generate_transaction(
        self,
        input_mint: str,
        output_mint: str,
        wallet_pub_key: str,
        amount_in: int,
    ) -> str:
        """
        Generate transaction for signing

        Args:
            input_mint (str): SPL token mint address
            output_mint (str): SPL token mint address
            wallet_pub_key (str): Your walet addres/public key
            amount_in (e.g. USDC = 6 decimals): amount in smallest units

        Returns:
            str:
                Transaction for signing
        """
        try:
            with self._lock:
                # Request transaction from Raydium
                wallet = wallet_pub_key
                if isinstance(wallet, str):
                    wallet = Pubkey.from_string(wallet_pub_key)

                in_mint = Pubkey.from_string(input_mint)
                out_mint = Pubkey.from_string(output_mint)

                input_ata = get_associated_token_address(wallet, in_mint)
                output_ata = get_associated_token_address(wallet, out_mint)

                compute_resp = self._compute_routes(input_mint, output_mint, amount_in)
                if not compute_resp:
                    raise RuntimeWarning("No available route for transaction!")
                price_impact_max = self._settings_get("sol_price_impact_lim")
                pi = compute_resp["data"]["priceImpactPct"]
                if pi > price_impact_max:
                    raise ValueError(f"Price impact is to big: asctual: {pi} > max: {price_impact_max}")
                
                priority_fee = self._unit_price_micro_lamports("h")
                if not priority_fee:
                    priority_fee = "15000"
                
                payload = {
                    "wallet": str(wallet),
                    "inputAccount": str(input_ata),
                    "outputAccount": str(output_ata),
                    "txVersion": "V0",
                    "wrapSol" : True,
                    "unwrapSol": True,
                    "computeUnitLimit": 300000,
                    "computeUnitPriceMicroLamports": str(priority_fee),
                    "swapResponse": compute_resp
                }
                resp_trx = requests.post(TRX_API_URL, json=payload, timeout=self._settings_get("sol_timeout"))
                resp_js = self._response_json(resp_trx)
                
                return resp_js["data"][0]["transaction"]
                    
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
                resp_js = self._compute_routes(input_mint, output_mint, amount_in)
                
                if resp_js["data"] is None:
                    raise ValueError(f"No data!")
                
                d = resp_js["data"]
                in_am = float(d["inputAmount"])
                out_am = float(d["outputAmount"])
                price =  in_am / out_am

                return price
    
        except Exception as e:
            self._logger.error(f"Raydium get_price() error: {e}")
            return False
    
    # Return price  
    # ---------------------------------------------------------
    def get_rpc(
        self
    ) -> str:
        """
        Compute price after routing.

        Returns:
            str:
                RPC with smallest weight
        """
        try:
            with self._lock:
                list_js = self._rpc_list()
                weight = 1000
                rpc = ""
                for resp_js in list_js:
                    if int(resp_js["weight"]) < weight:
                        weight = int(resp_js["weight"])
                        rpc = resp_js["url"]

                return rpc
    
        except Exception as e:
            self._logger.error(f"Raydium get_price() error: {e}")
            return False
    
    
    # Return data of pools used in routing
    # ---------------------------------------------------------
    def get_pools_info(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: int = 1_000_000_000
    ) -> list[dict]:
        """
        Compute exchange routs.

        Args:
            input_mint (str): SPL token mint address
            output_mint (str): SPL token mint address
            amount_in (e.g. USDC = 6 decimals): amount in smallest units

        Returns:
            list[dict]
                Full pool info:
                    {
                        "type": "Concentrated", 
                        "programId": "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK", 
                        "id": "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv", 
                        "mintA": {
                            "chainId": 101, 
                            "address": "So11111111111111111111111111111111111111112", 
                            "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", 
                            "symbol": "WSOL", 
                            "name": "Wrapped SOL", 
                            "decimals": 9, 
                            ...
                            }, 
                        "mintB": { ...
                            },
                        ...,                  
                        "price": 125.31715288497514, 
                        "mintAmountA": 119181.220202961, 
                        "mintAmountB": 1592306.047348, 
                        "feeRate": 0.0004, 
                        "openTime": "1723037622", 
                        "tvl": 16518790.88,
                        ...
                    },...
        """
        try:
            url = f"{DATA_BASE_URL}/pools/info/ids"

            routes = self.get_routes(input_mint, output_mint, amount_in)

            with self._lock:
                if not routes:
                    return False
                ids = []
                for route in routes:
                    ids.append(route["poolId"])

                ids_str = ", ".join(ids)
                params= {"ids" : ids_str}

                resp = requests.get(url, params=params)
                resp_js = self._response_json(resp)
                
                return resp_js["data"]
        
        except Exception as e:
            self._logger.error(f"Raydium get_pools_info() error: {e}")
            return False


   
    # Return rout plan 
    # ---------------------------------------------------------
    def get_routes(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: int = 1_000_000_000
    ) -> list[dict]:
        """
        Compute exchange routs.

        Args:
            input_mint (str): SPL token mint address
            output_mint (str): SPL token mint address
            amount_in (e.g. USDC = 6 decimals): amount in smallest units

        Returns:
            list[dict]
                routePlan:
                    {
                        "poolId": "xxxxxxxxxxxxxxxx", 
                        "inputMint": "xxxxxxxxxxxxxxxxx", 
                        "outputMint": "xxxxxxxxxxxxxxxx", 
                        "feeMint": "xxxxxxxxxxxxxx", 
                        "feeRate": 1, 
                        "feeAmount": "100", 
                        "remainingAccounts": ["xxxxxxxxxxxxxxxxx", "xxxxxxxxxxxxxxxxx"], 
                        "lastPoolPriceX64": "6474657900130872898"
                    },...
        """
        try:
            with self._lock:
                resp_js = self._compute_routes(input_mint, output_mint, amount_in)
            
            if not resp_js:
                raise ValueError(f"No route plans")
            
            if resp_js["data"] is None:
                raise ValueError(f"No data!")
            
            return resp_js["data"]["routePlan"]
    
        except Exception as e:
            self._logger.error(f"Raydium get_routes() error: {e}")
            return False

    # Helpers
    # ==================================================================
    # Get list of rpcs
    # ---------------------------------------------------------
    def _rpc_list(self) -> list[dict]:
        """
        Returns:
            list[dict]:
                List of available rpcs: 
                    {
                        "url": "https://raydium2-raydium2-d4b9.devnet.rpcpool.com/",
                        "batch": true,
                        "name": "Triton",
                        "weight": 100
                    },...
        """
        try:
            url = f"{DATA_BASE_URL}/main/rpcs"
            resp = requests.get(url)
            resp_js = self._response_json(resp)
            
            return resp_js["data"]["rpcs"]
    
        except Exception as e:
            self._logger.error(f"Raydium get_rpcs() error: {e}")
            return False


    # Get swapResponse routes for making a swap
    # ---------------------------------------------------------
    def _compute_routes(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: int
    ) -> dict:
        """
        Compute exchange routs.

        Args:
            input_mint: SPL token mint address (string)
            output_mint: SPL token mint address (string)
            amount_in: amount in smallest units (e.g. USDC = 6 decimals)

        Returns:
            swapResponse
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount_in,
                "slippageBps": str(self._settings_get("sol_slippage_bps")),
                "txVersion": "V0"
            }

            resp = requests.get(
                QUOTE_API_URL,
                params=params,
                timeout=self._settings_get("sol_timeout"),
            )
            
            resp_js = self._response_json(resp)
            return resp_js                
    
        except Exception as e:
            self._logger.error(f"Raydium _compute_routes() error: {e}")
            return False
    
    # Get auto-fee calculation select m h vh
    # ---------------------------------------------------------
    def _unit_price_micro_lamports(self, select: str = "h"):
        url = f"{DATA_BASE_URL}/main/auto-fee"
        resp = requests.get(url)
        resp_js = self._response_json(resp)

        return resp_js["data"]["default"][select]

    # Generate dict from response if successful
    # ---------------------------------------------------------
    @staticmethod
    def _response_json(resp: Response) -> dict:   
        if not resp.status_code == 200:
            raise ConnectionError(f"Response error status code: {resp.status_code}")
        resp_js = resp.json()    
              
        if not resp_js["success"]:
            raise ValueError(f"Response unsuccessful msg: {resp_js["msg"]}; id: {resp_js["id"]}")

        return resp_js
        