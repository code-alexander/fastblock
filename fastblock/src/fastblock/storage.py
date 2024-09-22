from fastblock.blockchain.projects.blockchain.smart_contracts.artifacts.storage.client import (
    StorageClient,
)

from base64 import b64decode
from algokit_utils import (
    Account,
    TransferParameters,
    transfer,
)
from algosdk.transaction import PaymentTxn
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from hashlib import sha256

from algokit_utils import OnSchemaBreak, OnUpdate

from functools import lru_cache

# load_dotenv(".env.localnet")

# algod = get_algod_client()
# indexer = get_indexer_client()
# account = get_localnet_default_account(algod)


def balance(algod: AlgodClient, account: Account | str) -> int:
    """Returns the balance of the specified account.

    Args:
        algod (AlgodClient): The Algod client.
        account (Account | str): The account or address.

    Returns:
        int: The account balance in MicroAlgos.
    """
    return algod.account_info(getattr(account, "address", account))["amount"]


def deploy_idempotent(
    account: Account, algod: AlgodClient, indexer: IndexerClient
) -> StorageClient:
    """Deploys the storage contract if it hasn't already been deployed.

    Funds the application account with the minimum balance required.

    Args:
        account (Account): The account that will deploy the contract.
        algod (AlgodClient): The Algod client.
        indexer (IndexerClient): The Indexer client.

    Returns:
        StorageClient: The storage contract client.
    """
    storage = StorageClient(
        algod,
        creator=account,
        indexer_client=indexer,
    )
    storage.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )

    if (current_balance := balance(algod, storage.app_address)) < 100_000:
        print(
            f"Funding storage app account with {(delta := 100_000 - current_balance)} microAlgos"
        )
        transfer(
            algod,
            TransferParameters(
                from_account=account,
                to_address=storage.app_address,
                micro_algos=delta,
            ),
        )

    return storage


def box_name(code: str) -> bytes:
    """Hashes the code to derive the box name (key).

    Args:
        code (str): The code to hash.

    Returns:
        bytes: The box name (key).
    """
    return b"content" + sha256(code.encode()).digest()


def storage_cost(code: str) -> int:
    """Calculates the box storage cost for the code provided.

    Reference: https://developer.algorand.org/articles/smart-contract-storage-boxes/
    Formula: 2500 + 400 * (len(n)+s)

    Args:
        code (str): The code to calculate the storage cost for.

    Returns:
        int: The storage cost in MicroAlgos.
    """
    name_length = 39  # 7 byte "content" prefix + 32 byte hash
    return 2_500 + 400 * (name_length + len(code))


def storage_payment_txn(
    storage: StorageClient, account: Account | str, algod: AlgodClient, amount: int
) -> PaymentTxn:
    """Returns a payment transaction object to fund the storage contract.

    Args:
        storage (StorageClient): The storage contract client.
        account (Account | str): The account to pay from.
        algod (AlgodClient): The Algod client.
        amount (int): The amount to pay in MicroAlgos.

    Returns:
        PaymentTxn: The payment transaction object.
    """
    return PaymentTxn(
        sender=getattr(account, "address", account),
        sp=algod.suggested_params(),
        receiver=storage.app_address,
        amt=amount,
    )


@lru_cache(maxsize=32)
def fetch_box(app_id: int, indexer: IndexerClient, box_name: bytes) -> str:
    """Returns the value of the specified box.

    Args:
        app_id (int): The storage contract app ID.
        indexer (IndexerClient): The Indexer client.
        box_name (bytes): The box name (key).

    Returns:
        str: The box value.
    """
    return b64decode(
        indexer.application_box_by_name(application_id=app_id, box_name=box_name)[
            "value"
        ]
    ).decode()


def fetch_boxes(app_id: int, indexer: IndexerClient) -> list[str]:
    """Returns the values of all boxes in the storage contract,
    up to the default limit.

    Args:
        app_id (int): The storage contract app ID.
        indexer (IndexerClient): The Indexer client.

    Returns:
        list[str]: The box values.
    """
    return [
        fetch_box(app_id, indexer, b64decode(x["name"]))
        for x in indexer.application_boxes(application_id=app_id)["boxes"]
    ]
