import logging

from src.models import Balance
from ..tokens.manager import TokenManager

from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.token.state import TokenAccount

from src.solana_api.constants import MAIN_RPC_URL

logger = logging.getLogger("solana")

def get_wallet_balances(wallet_pub: Pubkey, tokens: TokenManager) -> dict[str , Balance]:
    try:
        balance_dict = {}
        wallet_pubkey = wallet_pub
        if isinstance(wallet_pub, str):
            wallet_pubkey = Pubkey.from_string(wallet_pub)

        client = Client(MAIN_RPC_URL)

        resp = client.get_balance(wallet_pubkey)
        token = tokens.get_token("SOL")
        amount = resp.value / (10 ** token.decimals)
        locked = 0.01
        balance_dict[token.symbol]= Balance(
            available=max(amount-locked, 0.0),
            total=amount,
            locked=min(locked, amount)
        )

        token_options = TokenAccountOpts(
            program_id=TOKEN_PROGRAM_ID
        )
        resp = client.get_token_accounts_by_owner(
        wallet_pubkey, token_options
        )
        for acc in resp.value:
            token_acc = TokenAccount.from_bytes(acc.account.data)
            mint = token_acc.mint
            token = tokens.get_token_by_mint(mint)
            if not token:
                continue

            amount = token_acc.amount / (10 ** token.decimals)
            if amount > 0.000:
                balance_dict[token.symbol]= Balance(
                    available=amount,
                    total=amount,
                    locked=0
                )

        return balance_dict


    except Exception as e:
        logger = logging.error(f"Error fetching token info: {e}")
