function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// console.log("Hello");
// sleep(2000).then(() => {
//   console.log("World!");
// });

// document.addEventListener("DOMContentLoaded", connect());

document.addEventListener("change", () => {
  console.log("something changed");
});

const connectButton = document.getElementById("connect-button");
let accountAddress = "";

let counter = 0;

const codeSnippet = document.getElementById("code-snippet");

// console.log("code-snippet", codeSnippet);

connectButton.addEventListener("click", (event) => {
  //   console.log("event:", event);
  //   console.log("click counter:", counter);
  console.log("account address:", accountAddress);
  if (accountAddress) {
    handleDisconnectWalletClick(event);
  } else {
    handleConnectWalletClick(event);
  }
});

function handleConnectWalletClick(event) {
  //   event.preventDefault();

  htmx.trigger("#connect-button", "wallet-connect");

  console.log("Connecting to mock wallet...");

  setTimeout(1000);

  accountAddress = "test-address";

  connectButton.innerHTML = "Disconnect";

  codeSnippet.style = "display:block;";

  // sleep(2000).then(() => {
  //   console.log("World!");
  // });
}

function handleDisconnectWalletClick(event) {
  console.log("Disconnecting wallet...");
  accountAddress = "";
  connectButton.innerHTML = "Connect";

  codeSnippet.style = "display:none;";
}

function handleUploadClick(event) {
  //   event.preventDefault();

  console.log("Uploading...");

  setTimeout(1000);

  // sleep(2000).then(() => {
  //   console.log("World!");
  // });
}
