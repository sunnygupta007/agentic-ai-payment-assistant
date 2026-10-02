function readStoredInvoices() {
  try {
    return JSON.parse(localStorage.getItem("agentic-invoices") || "[]");
  } catch {
    localStorage.removeItem("agentic-invoices");
    return [];
  }
}

window.AppState = {
  sessionId: localStorage.getItem("agentic-session") || "demo-session",
  socket: null,
  currentApproval: null,
  dashboard: null,
  invoices: readStoredInvoices(),
  selectedInvoiceId: null,
  assistantBuffer: "",
  assistantBubble: null,
};
