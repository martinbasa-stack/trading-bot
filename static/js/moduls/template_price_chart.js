// chartTemplate.js

export function createCandleChart(canvasId) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  const chart = new Chart(ctx, {
    type: "candlestick",

    data: {
      datasets: [
        {
          label: "Price",
          data: [],              
          parsing: false
        }
      ]
    },

    options: {
      responsive: true,
      normalized: true,
      animation: false,
      parsing: false,

      interaction: {
        mode: 'x',
        intersect: false,
        axis: 'x'
      },

      scales: {
        x: {
          type: "time",
          ticks: {
            source: "data",
            autoSkip: true,
            maxTicksLimit: 12
          }          
        },
        y: {
          position: "right"
        }
      },

      plugins: {
        tooltip: {
          mode: 'x',
          intersect: false,
          position: 'cursor',

          callbacks: {
            label(context) {
              const raw = context.raw;
              const label = context.dataset.label;

              if (label === 'Price') {
                return [
                  `O: ${raw.o}`,
                  `H: ${raw.h}`,
                  `L: ${raw.l}`,
                  `C: ${raw.c}`
                ];
              }

              if (label === 'Trades') {
                let time = new Date(raw.x)
                  .toISOString()
                  .replace('T', ' ')
                  .slice(0, 19);

                return `Trade: ${raw.y} @ ${time} (${raw.side})`;
              }

              return `${label}: ${raw.y}`;
            }
          }
        },       

        zoom: {
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'x',
            onZoom: ({ chart }) => {
              syncZoom(chart, volumeChart);
            }
          },
          
          pan: {
          enabled: true,
          mode: 'x',
          onPan: ({ chart }) => {
            syncZoom(chart, volumeChart);
            }
          }
        }
      }
    }
  });

  return chart;
}



