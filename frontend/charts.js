function drawCategoryChart(items = [], canvasId = "categoryChart") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const container = canvas.parentElement;
  if (!container) return;

  const rect = container.getBoundingClientRect();

  if (rect.width < 50 || rect.height < 50) return;

  const ctx = canvas.getContext("2d");

  const dpr = window.devicePixelRatio || 1;

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, rect.width, rect.height);

  const total =
    items.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1;

  const colors = ["#32d296", "#58a6ff", "#f7c948", "#ff6b6b", "#a78bfa"];

  const size = Math.min(rect.width, rect.height);

  const cx = rect.width / 2;
  const cy = rect.height / 2;

  const radius = size * 0.35;

  let start = -Math.PI / 2;

  items.forEach((item, index) => {
    const angle = (Number(item.value || 0) / total) * Math.PI * 2;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();

    ctx.fillStyle = colors[index % colors.length];
    ctx.fill();

    start += angle;
  });

  ctx.fillStyle = getComputedStyle(document.body)
    .getPropertyValue("--surface-strong")
    .trim();

  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = getComputedStyle(document.body)
    .getPropertyValue("--text")
    .trim();

  ctx.font = "700 18px Inter, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.fillText("Spend", cx, cy);

  if (!items.length) {
    ctx.fillStyle = "#8fa8a0";
    ctx.font = "500 14px Inter, sans-serif";
    ctx.fillText("No spending data", cx, cy + 28);
  }
}
