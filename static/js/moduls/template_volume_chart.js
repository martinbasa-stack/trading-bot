export function createVolumeChart(canvasId) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  const chart = new Chart(ctx, {
    type: "bar",

    data: {
      datasets: [{
        label: "Volume",
        data: [],
        parsing: false,
        backgroundColor: ctx => ctx.raw?.color
      }]
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
        legend: { display: false }
      },
      tooltip: {
        mode: 'x',
        intersect: false,
        position: 'cursor'
      }
    }
  });

  return chart;
}
