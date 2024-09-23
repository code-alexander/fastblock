# ruff: noqa: F403
# ruff: noqa: F405
from fasthtml.common import *
from pathlib import Path
from textwrap import dedent
from algokit_utils import (
    TransactionParameters,
    get_algod_client,
    get_indexer_client,
    get_algonode_config,
    is_localnet,
)
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk.encoding import msgpack_encode
from algosdk.error import IndexerHTTPError
from algokit_utils.logic_error import LogicError
import json
from fastblock.src.fastblock.storage import (
    deploy_idempotent,
    fetch_box,
    storage_cost,
    storage_payment_txn,
    box_name,
    fetch_boxes,
    StorageClient,
)
from fastblock.src.fastblock.account import account_from_keyring


app = FastHTML(
    hdrs=(
        picolink,
        HighlightJS(langs=["python", "javascript"]),
        Script(src="https://unpkg.com/algosdk@v2.9.0/dist/browser/algosdk.min.js"),
        Script(
            src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"
        ),
        Style(open(Path(__file__).parent / "style.css").read()),
    ),
    key_fname="/tmp/.sesskey",
)


def dependencies(
    app_id: int | None = None
) -> tuple[AlgodClient, IndexerClient, StorageClient]:
    """Returns Algod, Indexer, and storage app clients.

    Deploys the storage contract if it hasn't already been deployed.

    Returns:
        tuple[AlgodClient, IndexerClient, StorageClient]: Algod, Indexer, and storage app clients.
    """
    algod = get_algod_client(get_algonode_config("mainnet", "algod", ""))
    indexer = get_indexer_client(get_algonode_config("mainnet", "indexer", ""))

    if app_id:
        return algod, indexer, StorageClient(algod, app_id=app_id)

    account = account_from_keyring("MAINNET", "DEPLOYER")
    storage = deploy_idempotent(account, algod, indexer)
    print(f"{storage.app_id = }")

    code = dedent(
        """\
        print("Welcome to Code Snippet!")
        '''
        This code is stored on the Algorand blockchain :)
        Connect your wallet to upload and share your own snippets!
        '''
        """
    )

    try:
        storage.store(
            payment=TransactionWithSigner(
                storage_payment_txn(storage, account, algod, storage_cost(code)),
                AccountTransactionSigner(account.private_key),
            ),
            code=code,
            transaction_parameters=TransactionParameters(boxes=[(0, box_name(code))]),
        )
    except LogicError as e:
        # Might be a better way to do this
        if e.pc == 88:
            print("Content already stored")
        else:
            raise e

    return algod, indexer, storage


@app.get("/txns")
def get_txns(sender: str, code: str):
    """Returns the encoded transactions to sign.

    Args:
        sender (str): The sender's address.
        code (str): The code snippet to upload.

    Returns:
        str: A JSON array of base64-encoded transactions.
    """
    algod, indexer, storage = dependencies(app_id=2302451247)
    storage.signer = AccountTransactionSigner("")
    storage.sender = sender

    unsigned_txns = (
        storage.compose()
        .store(
            payment=TransactionWithSigner(
                storage_payment_txn(storage, sender, algod, storage_cost(code)),
                AccountTransactionSigner(""),
            ),
            code=code,
            transaction_parameters=TransactionParameters(boxes=[(0, box_name(code))]),
        )
        .build()
        .build_group()
    )
    return json.dumps([msgpack_encode(x.txn) for x in unsigned_txns])


def snippet(id: str | None, uploaded: bool, request_count: int = 0):
    """Reads a snippet from box storage.

    If no ID is provided, the default snippet is displayed.
    Otherwise, the indexer is polled every second until the snippet is found.
    If the snippet is not found after 10 requests, an error message is displayed.

    Args:
        id (str | None): The snippet ID to search for.
        uploaded (bool): True if the snippet has been uploaded by the user.
        request_count (int, optional): The number of requests made. Defaults to 0.
    """
    algod, indexer, storage = dependencies(app_id=2302451247)

    if not id:
        code = next(
            iter(fetch_boxes(app_id=storage.app_id, indexer=indexer)),
            "# No snippets created yet :(",
        )
        return Div(Pre(Code(code)), id="code-snippet")
    if request_count > 10:
        return Div(Card(f"Could not find snippet {id}."), id="code-snippet")
    try:
        code = fetch_box(
            app_id=storage.app_id,
            indexer=indexer,
            box_name=b"content" + bytes.fromhex(id),
        )
        return Div(
            P(
                "Congratulations! 🥳 Your snippet is stored on Algorand:"
                if uploaded
                else ""
            ),
            Pre(Code(code)),
            id="code-snippet",
        )
    except IndexerHTTPError:
        return Div(
            Card(
                P("Waiting for indexer...", aria_busy="true"),
                Progress(value=request_count, max=10),
            ),
            id="code-snippet",
            hx_post=f"/snippet/{id}/{uploaded}/{request_count + 1}",
            hx_trigger="every 1s",
            hx_swap="outerHTML",
        )


@app.post("/snippet/{id}/{uploaded}/{request_count}")
def post(id: str, uploaded: bool, request_count: int):
    return snippet(id, uploaded, request_count)


@app.route("/")
def get(id: str | None = None, uploaded: bool | None = None):
    title = "Code Snippet"
    algod, indexer, storage = dependencies(app_id=2302451247)
    network = "localnet" if is_localnet(algod) else "mainnet"

    pera = Script(
        open(Path(__file__).parent / "bundle.js").read(),
        type="module",
    )

    upload_section = Div(
        Input(
            id="code-input",
            name="code",
            placeholder="Paste your code here...",
            style="min-height: 100px;",
        ),
        Button("Upload", id="upload-button", action="/", method="post", cls="contrast"),
        id="upload-section",
        style="display: none;",
    )

    explainer = Div(
        P(
            "Code snippets are stored in application ",
            A(
                f"#{storage.app_id}.",
                href=f"https://lora.algokit.io/{network}/application/{storage.app_id}",
                target="_blank",
            ),
        ),
        P(
            "Each snippet resides in a separate box, referenced by the hash of its contents."
        ),
        P("You'll be charged a small fee with each upload to cover the storage costs."),
    )

    return (
        Title(title),
        Header(
            Div(
                Button(
                    "Connect",
                    id="connect-button",
                    cls="contrast",
                    style="width:125px; margin-bottom: 10px;",
                ),
                cls="container",
                style="display: flex; justify-content: flex-end; border-bottom: 1px solid #e5e7eb;",
            ),
        ),
        Main(
            H1(title),
            snippet(id, uploaded),
            upload_section,
            cls="container",
        ),
        pera,
        Footer(
            H3("How does it work?"),
            explainer,
            cls="container",
            style="margin-top: 16px; border-top: 1px solid #e5e7eb;",
        ),
    )


# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         port=5000,
#         reload=True,
#         ssl_certfile="./localhost+1.pem",
#         ssl_keyfile="./localhost+1-key.pem",
# #     )

serve()
