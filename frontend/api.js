const API = {
  base: location.port === "3000" ? "http://localhost:8000" : "",
  async createSession() {
    const res = await fetch(`${this.base}/api/session/create`, { method: "POST" });
    return res.json();
  },
  async dashboard(sessionId) {
    const res = await fetch(`${this.base}/api/dashboard/${sessionId}`);
    return res.json();
  },
  async decideApproval(id, decision) {
    const res = await fetch(`${this.base}/api/approvals/${id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    return res.json();
  },
  async topUpWallet(sessionId, amount, source = "ui") {
    const res = await fetch(`${this.base}/api/wallet/top-up`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, amount, source }),
    });
    if (!res.ok) throw new Error("Top-up failed");
    return res.json();
  },
};
