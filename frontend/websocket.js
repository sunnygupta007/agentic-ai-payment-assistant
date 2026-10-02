function connectSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const host = location.port === "3000" ? "localhost:8000" : location.host;
  const socket = new WebSocket(`${proto}://${host}/ws/chat/${AppState.sessionId}`);
  AppState.socket = socket;

  socket.onopen = () => addChip("Realtime connected");
  socket.onclose = () => {
    addChip("Reconnecting...");
    setTimeout(connectSocket, 1200);
  };
  socket.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "agent") addChip(`${data.agent}: ${data.status}`);
    if (data.type === "tool") addChip(`${data.tool}: ${data.status}`);
    if (data.type === "typing") document.querySelector(".composer").classList.toggle("shimmer", data.payload.active);
    if (data.type === "token") {
      if (!AppState.assistantBubble) AppState.assistantBubble = addMessage("assistant", "");
      AppState.assistantBuffer += data.content;
      AppState.assistantBubble.textContent = AppState.assistantBuffer;
    }
    if (data.type === "approval") {
      addApprovalQueueCard(data.payload);
      switchTab("approvals");
      showToast("Added to approval queue");
    }
    if (data.type === "invoice") {
      addInvoice(data.payload);
      switchTab("invoices");
      showToast(`Invoice ${data.payload.invoice_id} generated`);
    }
    if (["transaction", "analytics", "recurring", "wallet"].includes(data.type)) {
      showToast(`${data.type} update received`);
      await refreshDashboard();
    }
    if (data.type === "final") {
      if (!AppState.assistantBubble) addMessage("assistant", data.content);
      AppState.assistantBuffer = "";
      AppState.assistantBubble = null;
      await refreshDashboard();
    }
  };
}

function sendSocketMessage(message) {
  if (!AppState.socket || AppState.socket.readyState !== WebSocket.OPEN) {
    showToast("Realtime socket is reconnecting");
    return;
  }
  AppState.socket.send(JSON.stringify({ message }));
}
