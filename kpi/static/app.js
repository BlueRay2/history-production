// Vanilla JS only — renders retention curves via Chart.js if present.
document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("retention-chart");
  if (!canvas || typeof Chart === "undefined") return;
  const curves = JSON.parse(canvas.dataset.curves || "[]");
  if (!curves.length) return;

  const datasets = curves.map((c, i) => ({
    label: c.title || c.video_id,
    data: (c.points || []).map(p => ({ x: p[0], y: p[1] })),
    fill: false,
    borderWidth: 1.5,
    tension: 0.1,
  }));

  new Chart(canvas, {
    type: "line",
    data: { datasets },
    options: {
      parsing: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } },
      scales: {
        x: { type: "linear", title: { display: true, text: "Elapsed (s)" } },
        y: { title: { display: true, text: "Retention %" }, min: 0, max: 100 },
      },
    },
  });
});
