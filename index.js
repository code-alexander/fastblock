import { PeraWalletConnect } from "@perawallet/connect";

const peraWallet = new PeraWalletConnect();

// Create an instance of the algod client
const algod = new algosdk.Algodv2(
  "",
  "https://mainnet-api.algonode.cloud",
  443
);

let accountAddress = "";

const connectButton = document.getElementById("connect-button");
connectButton.addEventListener("click", (event) => {
  if (accountAddress) {
    handleDisconnectWalletClick(event);
  } else {
    handleConnectWalletClick(event);
  }
});

const uploadSection = document.getElementById("upload-section");
const codeInput = document.getElementById("code-input");
const uploadButton = document.getElementById("upload-button");

document.addEventListener("DOMContentLoaded", reconnectSession);

uploadButton.addEventListener("click", (event) => {
  event.preventDefault();

  // Set loading spinner
  uploadButton.setAttribute("aria-busy", "true");

  console.log("Requesting signature from account", accountAddress);

  if (codeInput.value) {
    const contentHash = CryptoJS.SHA256(codeInput.value).toString();
    fetch(
      `/txns?sender=${accountAddress}&code=${encodeURIComponent(
        codeInput.value
      )}`,
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    )
      .then((response) => response.json())
      .then(async (data) => {
        const txns = data.map((item) => {
          return {
            txn: algosdk.decodeUnsignedTransaction(Buffer.from(item, "base64")),
            signers: [accountAddress],
          };
        });

        try {
          const signedTxns = await peraWallet.signTransaction([txns]);
          const { txId } = await algod.sendRawTransaction(signedTxns).do();
          console.log("Transaction ID:", txId);
          console.log("Content hash:", contentHash);

          // Remove loading spinner
          uploadButton.setAttribute("aria-busy", "false");

          if (txId && contentHash) {
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set("id", contentHash);
            currentUrl.searchParams.set("uploaded", true);
            // Redirect
            window.location.href = currentUrl.toString();
          }
        } catch (error) {
          console.log("Transaction signing failed:", error);
        }
      })
      .catch((error) => console.error("Error:", error));
  }
});

function reconnectSession() {
  // Reconnect to the session when the component is mounted
  peraWallet
    .reconnectSession()
    .then((accounts) => {
      peraWallet.connector?.on("disconnect", handleDisconnectWalletClick);

      if (accounts.length) {
        accountAddress = accounts[0];
        connectButton.innerHTML = "Disconnect";
        uploadSection.style.display = "block";
      }
    })
    .catch((e) => console.log(e));
}

function handleConnectWalletClick(event) {
  event.preventDefault();

  peraWallet
    .connect()
    .then((newAccounts) => {
      peraWallet.connector.on("disconnect", handleDisconnectWalletClick);

      accountAddress = newAccounts[0];

      connectButton.innerHTML = "Disconnect";
      uploadSection.style.display = "block";
    })
    .catch((error) => {
      if (error?.data?.type !== "CONNECT_MODAL_CLOSED") {
        console.log(error);
      }
    });
}

function handleDisconnectWalletClick(event) {
  peraWallet.disconnect().catch((error) => {
    console.log(error);
  });

  accountAddress = "";

  connectButton.innerHTML = "Connect";
  uploadSection.style.display = "none";
}
