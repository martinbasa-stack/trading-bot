export function createEmptyChart(canvasId) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  const chart = new Chart(ctx, {
    type: "line",

    data: {
      datasets: []
    },

    options: {
      responsive: true,
      animation: false,
      interaction: { mode: "x", intersect: false },

      scales: {
        x: {
          type: "time",
          display: false,
          min: undefined,
          max: undefined
        },
        y: { position: "right" }
      },

      plugins: {
        legend: { display: true }
      },
      tooltip: {
        mode: 'x',
        intersect: false,
        position: 'cursor',
        callbacks: {
          label(context) {
            const raw = context.raw;
            const label = context.dataset.label;

            return `${label}: ${raw.y}`;
            
          }
        }
      }
    }
  });

  return chart;
}
