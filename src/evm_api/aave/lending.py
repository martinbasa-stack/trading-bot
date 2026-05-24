from .constants import WITHDRAW_URL, MARKET_PUB_KEY, DEPOSIT_URL, MAIN_MARKET_URL
from .models import UserBalances

import requests
from requests import Response
import json
import logging
import threading
from datetime import datetime, timezone


class AaveLending:
    """
    Aave Lending interaction getting pool data and generating transaction for deposit and withdraw.
    """

    def __init__(
        self
    ):
        self._reserves : dict = {}
        """
        Parameters:
            dict[reserve,dict]:
                Reserve metrics:
                    {
                        "reserve": "64AZMUHLB6NYvQSt41JTer4v8NAFDCz5sUPb7dYpCxa",
                        "liquidityToken": "adraSOL",
                        "liquidityTokenMint": "sctmY8fJucsJatwHz6P48RuWBBkdBMNmSMuBYrWFdrw",
                        "maxLtv": "0.45",
                        "borrowApy": "0.012932792149291661",
                        "supplyApy": "0",
                        "totalSupply": "128.6929917969596136963225546673977861544",
                        "totalBorrow": "0.0000000000000004610998013514222559905419984715990722179",
                        "totalBorrowUsd": "0.00000000000006086444658766384012347515378927208466036",
                        "totalSupplyUsd": "16987.27195820889910490812593516043118697"
                    }
        """
        self._token_reserve : dict = {}
        """
        token_mint : reserve                   
        """
        self._user_deposits : dict[str, UserBalances] = {}
        self._lock = threading.Lock()

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("solana").getChild(self.__class__.__name__)

        self._load_pools()
    
    def generate_deposit_transaction(self, wallet_pub: str, token_mint: str, amount : float) -> str:

        if isinstance(wallet_pub, Pubkey):
            wallet_pub = str(wallet_pub)

        if token_mint not in self._token_reserve:
            raise RuntimeWarning(f"Token: '{token_mint}' does not have a reserve pool on main market!")
        
        reserve = self._token_reserve[token_mint]
        with self._lock:
            headers = { "Content-Type": "application/json" }
            body = {
                "wallet": wallet_pub,
                "market": MARKET_PUB_KEY,
                "reserve": reserve,
                "amount": str(amount)
                }
            url = DEPOSIT_URL
            resp =  requests.post(
                url,
                headers=headers,
                data=json.dumps(body)
                )
            resp_js = self._response_json(resp)
            tx = resp_js["transaction"]

            return tx
        
    def generate_withdraw_transaction(self, wallet_pub: str, token_mint: str, amount : float) -> str:

        if isinstance(wallet_pub, Pubkey):
            wallet_pub = str(wallet_pub)
        
        with self._lock:

            if token_mint not in self._user_deposits:
                raise RuntimeWarning(f"No user deposits for token: '{token_mint}'")
            
            dep = self._user_deposits[token_mint]
            if amount > dep.amount:
                amount = dep.amount * 0,99 # Leave a 1% on the exchange to not close the vault reopening cost 2x more
            amount = round(amount, dep.decimals)

            headers = { "Content-Type": "application/json" }
            body = {
                "wallet": wallet_pub,
                "market": MARKET_PUB_KEY,
                "reserve": dep.reserve,
                "amount": str(amount)
                }
            url = WITHDRAW_URL
            resp =  requests.post(
                url,
                headers=headers,
                data=json.dumps(body)
                )
            resp_js = self._response_json(resp)
            tx = resp_js["transaction"]

            return tx
    
    def get_token_deposit(self, token_mint) -> UserBalances:
        """
        Args:
            token_mint(str):
                Public wallet address as string.
        Returns:
            UserBalances:
                If no balance return None.                 
        """
        with self._lock:
            if token_mint not in self._user_deposits:
                return
            
            return self._user_deposits[token_mint]

        
    def get_all_deposits(self, wallet_pub: str) -> dict[str, UserBalances]:
        """
        Fills local data dictionary and returns it.
        Args:
            wallet_pub(str):
                Mint address of token as string.
        Returns:
            dict[str, UserBalances]:
                All user deposits token mint as key.                        
        """
        if isinstance(wallet_pub, Pubkey):
            wallet_pub = str(wallet_pub)
            
        with self._lock:
            usre_reserves = self._user_reserve_deposits(wallet_pub)
            for d in usre_reserves:
                if int(d["depositedAmount"]) > 0:
                    reserve = d["depositReserve"]
                    r = self._full_reserve_metrics(reserve)                    
                    if not r:
                        continue
                    amount =  float(d["depositedAmount"]) / float(r["exchangeRate"]) / 10 ** int(r["decimals"])
                    self._user_deposits[r["mintAddress"]] = UserBalances(
                        token_mint= r["mintAddress"],
                        token_simbol= r["symbol"],
                        amount= round(amount, int(r["decimals"])),
                        decimals= int(r["decimals"]),
                        exchange_rate= float(r["exchangeRate"]),
                        k_amount= int(d["depositedAmount"]),
                        reserve= reserve,
                        supply_apy= float(self._reserves[reserve]["supplyApy"])
                    )
            return self._user_deposits
                

    def get_reserve_basic(self, token_mint: str) -> dict:
        """
        Args:
            token_mint(str):
                Mint address of token as string.
        Returns:
            dict:
                Basic data of a reserve:
                    {
                        "reserve": "64AZMUHLB6NYvQSt41JTer4v8NAFDCz5sUPb7dYpCxa",
                        "liquidityToken": "adraSOL",
                        "liquidityTokenMint": "sctmY8fJucsJatwHz6P48RuWBBkdBMNmSMuBYrWFdrw",
                        "maxLtv": "0.45",
                        "borrowApy": "0.012932792149291661",
                        "supplyApy": "0",
                        "totalSupply": "128.6929917969596136963225546673977861544",
                        "totalBorrow": "0.0000000000000004610998013514222559905419984715990722179",
                        "totalBorrowUsd": "0.00000000000006086444658766384012347515378927208466036",
                        "totalSupplyUsd": "16987.27195820889910490812593516043118697"
                    }
        """

        with self._lock:                
            pool = None
            apy = 0.0
            for _, d in self._reserves.items():
                if d["liquidityTokenMint"] == token_mint:
                    if apy < float(d["supplyApy"]):
                        apy = float(d["supplyApy"])
                        pool = d
        return pool
    

    def _load_pools(self):
        try:
            url = f"{MAIN_MARKET_URL}/reserves/metrics"
            params = {
                "env": "mainnet-beta",
            }

            resp = requests.get(
                url,
                params=params                                    
                )
            resp_js = self._response_json(resp)
            for d in resp_js:
                self._reserves[d["reserve"]] = d
                self._token_reserve[d["liquidityTokenMint"]]= d["reserve"]               
    
        except Exception as e:
            self._logger.error(f"load pools error: {e}")

    def _full_reserve_metrics(self, reserve:str) -> dict:
        """
        Full reserve data
        Args:
            reserve(str):
                Reserve addresss.
        Returns:
            dict:
                Full reserve data:
                    {
                        "status": "Active",
                        "symbol": "USDC",
                        "decimals": 6,
                        "borrowTvl": "306110285.3905348063072914661349560815503",
                        "depositTvl": "444253409.26174457439",
                        "borrowCurve": [],
                        "loanToValue": 0.8,
                        "mintAddress": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "totalSupply": "444378048.4167645085",
                        "borrowFactor": 100,
                        "exchangeRate": "0.85560881084262899886",
                        "totalBorrows": "306196167.2915367365311537241315004848063",
                        "assetPriceUSD": "0.9998210399999999994230526212390941509511",
                        "totalLiquidity": "138210417.562418",
                        "mintTotalSupply": "380213774.062019",
                        "protocolTakeRate": 0.1,
                        "borrowInterestAPY": 0.044807168549707344,
                        "supplyInterestAPY": 0.027554982810050976,
                        "reserveBorrowLimit": "700000000000000",
                        "assetOraclePriceUSD": "0.99971952",
                        "maxLiquidationBonus": 0.1,
                        "minLiquidationBonus": 0.01,
                        "reserveDepositLimit": "1000000000000000",
                        "liquidationThreshold": 0.9,
                        "hostFixedInterestRate": "0",
                        "accumulatedProtocolFees": "28536.43719022803128692696562375419322422",
                        "borrowLimitCrossedTimestamp": 0,
                        "borrowOutsideElevationGroup": "305022993761866",
                        "depositLimitCrossedTimestamp": 0,
                        "borrowLimitOutsideElevationGroup": "18446744073709551615",
                        "borrowedAgainstCollateralInElevationGroups": [],
                        "borrowLimitAgainstCollateralInElevationGroups": []
                    }
        """
        try:
            resp_js = None
            url = f"{MAIN_MARKET_URL}/reserves/{reserve}/metrics/history"
            now = int(datetime.now(timezone.utc).timestamp())
            td = datetime.fromtimestamp(now - 3600,timezone.utc)

            params = {
                "env": "mainnet-beta",
                "start": f"{td.year}-{td.month:02d}-{td.day:02d}T{td.hour:02d}:00Z",
                "frequency": "hour"
            }
            
            resp = requests.get(
                url,
                params=params                                    
                )
            resp_js = self._response_json(resp)
            if not resp_js.get("history"):
                raise RuntimeError("No data recived!")
            
            return  resp_js["history"][-1]["metrics"]   
    
        except Exception as e:
            raise RuntimeError(f"_full_reserve_metrics error: {repr(e)} response: {resp_js}")

    def _user_reserve_deposits(self, wallet_pub: str) -> list[dict]:
        """
        Get reserve deposits
        Args:
            wallet_pub(str):
                String of public wallet address
        Returns:
            list[dict]:
                The list of reserves not token mints:
                    [{
                        "depositReserve": "EVbyPKrHG6WBfm4dLxLMJpUDY43cCAcHSpV3KYjKsktW",
                        "depositedAmount": "152484459524",
                        "marketValueSf": "38759113134866650605052",
                        "borrowedAmountAgainstThisCollateralInElevationGroup": "0",
                        "padding": []
                    },]
        """
        url = f"{MAIN_MARKET_URL}/users/{wallet_pub}/obligations"
        params = {
            "env": "mainnet-beta",
        }
        try:
            resp_js = None
            resp = requests.get(
                url,
                params=params                                    
                )
            resp_js = self._response_json(resp)
            if not resp_js:
                raise RuntimeError("No data recived!")
            
            return resp_js[0]["state"]["deposits"]
        except Exception as e:
            raise RuntimeError(f"_user_reserve_deposits error: {repr(e)} response: {resp_js}")
    

    # Generate dict from response if successful
    # ---------------------------------------------------------
    @staticmethod
    def _response_json(resp: Response) -> dict:   
        if not resp.status_code == 200:
            raise ConnectionError(f"Response error status code: {resp.status_code} data:{resp.json()}")
        resp_js = resp.json()    
              
        return resp_js