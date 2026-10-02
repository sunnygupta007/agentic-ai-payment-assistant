async function init() {
  document.body.classList.toggle("light", localStorage.getItem("theme") === "light");
  await refreshDashboard();
  connectSocket();

  document.querySelectorAll(".tab-btn").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  document.querySelectorAll("[data-tab-jump]").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tabJump));
  });

  document.addEventListener("click", (event) => {
    const tabButton = event.target.closest("[data-tab]");
    const tabJump = event.target.closest("[data-tab-jump]");
    if (tabButton) switchTab(tabButton.dataset.tab);
    if (tabJump) switchTab(tabJump.dataset.tabJump);
  });

  document.querySelectorAll("[data-open-topup]").forEach((button) => {
    button.addEventListener("click", () => openTopUpModal());
  });

  document.querySelectorAll(".preset-btn").forEach((button) => {
    button.addEventListener("click", () => openTopUpModal(button.dataset.amount));
  });

  document.getElementById("closeTopUp").addEventListener("click", () => {
    document.getElementById("topUpModal").close();
  });

  document.getElementById("topUpForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitTopUp(document.getElementById("topUpAmount").value, "ui");
  });

  document.getElementById("chatForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    if (!message) return;
    switchTab("chat");
    addMessage("user", message);
    input.value = "";
    AppState.assistantBuffer = "";
    AppState.assistantBubble = null;
    sendSocketMessage(message);
  });

  document.querySelectorAll(".quick").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab("chat");
      document.getElementById("chatInput").value = btn.dataset.prompt;
      document.getElementById("chatForm").requestSubmit();
    });
  });

  document.getElementById("newChatBtn").addEventListener("click", async () => {
    const session = await API.createSession();
    AppState.sessionId = session.session_id;
    localStorage.setItem("agentic-session", AppState.sessionId);
    document.getElementById("messages").innerHTML = "";
    addMessage("assistant", "New demo session created. What would you like to simulate?");
    if (AppState.socket) AppState.socket.close();
    await refreshDashboard();
    connectSocket();
  });

  document.getElementById("themeToggle").addEventListener("click", () => {
    document.body.classList.toggle("light");
    localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark");
    renderChartsForActiveTab();
  });

  document.getElementById("approveApproval").addEventListener("click", async () => {
    if (!AppState.currentApproval?.id) return;
    await API.decideApproval(AppState.currentApproval.id, "approved");
    document.getElementById("approvalModal").close();
    showToast("Simulated approval accepted");
    await refreshDashboard();
  });

  document.getElementById("rejectApproval").addEventListener("click", async () => {
    if (!AppState.currentApproval?.id) return;
    await API.decideApproval(AppState.currentApproval.id, "rejected");
    document.getElementById("approvalModal").close();
    showToast("Simulated approval rejected");
    await refreshDashboard();
  });
}

init().catch((error) => {
  console.error(error);
  showToast("Could not start demo UI. Is the backend running?");
});
