# ruff: noqa: E731
import keyring
from algokit_utils import Account, get_account_from_mnemonic
from getpass import getpass
from typing import TypeAlias, Literal

AlgorandNetworkChoice: TypeAlias = Literal["LOCALNET", "TESTNET", "MAINNET"]

service = lambda network: f"fastblock_{network}"


def account_from_keyring(network: AlgorandNetworkChoice, name: str) -> Account:
    mnemonic = keyring.get_password(service(network), name)
    if not mnemonic:
        raise ValueError(f"{service(network)} account '{name}' not found in keyring")
    return get_account_from_mnemonic(mnemonic)


def store_account_in_keyring(network: AlgorandNetworkChoice, name: str) -> Account:
    if keyring.get_password(service(network), name):
        raise ValueError(
            f"{service(network)} account '{name}' already exists in keyring"
        )
    keyring.set_password(
        service(network), name, getpass(f"Enter mnemonic for '{name}': ")
    )
    return account_from_keyring(network, name)
