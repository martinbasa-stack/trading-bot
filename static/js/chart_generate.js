// chartController.js
import { createCandleChart } from './moduls/template_price_chart.js';
import { createVolumeChart } from './moduls/template_volume_chart.js';
import { createEmptyChart } from './moduls/template_empty_chart.js';

const zoomLinks = new Map(); // sourceChart -> Set(targetCharts)
// === GLOBAL RESET REGISTRY ===
const resetLinks = new Map();  // canvas -> Set(charts)

const hoverLinks = new Map();   // chart -> Set(charts)

// ===== 1. LOAD DATA =====
const candleData = JSON.parse(
  document.getElementById('candles_json').dataset.json
);
const tradeData = JSON.parse(
  document.getElementById('trades_json').dataset.json
);
const strategyData = JSON.parse(
  document.getElementById('strategy').dataset.json
);
const avgs = JSON.parse(
  document.getElementById('avgs').dataset.json
);
const integratedInd = JSON.parse(
  document.getElementById('price_indic').dataset.json
);
const soloInd = JSON.parse(
  document.getElementById('solo_indic').dataset.json
);


function linkZoom(source, target) {
  if (!zoomLinks.has(source)) {
    zoomLinks.set(source, new Set());
  }
  zoomLinks.get(source).add(target);
}

function handleZoom({ chart }) {
  const targets = zoomLinks.get(chart);
  if (!targets) return;

  const min = chart.scales.x.min;
  const max = chart.scales.x.max;

  for (const target of targets) {
    target.options.scales.x.min = min;
    target.options.scales.x.max = max;
    target.update('none'); // no feedback loop
  }
}

function attachResetZoom(canvas, chart) {
  if (!resetLinks.has(canvas)) {
    resetLinks.set(canvas, new Set());

    canvas.addEventListener('dblclick', () => {
      for (const c of resetLinks.get(canvas)) {
        c.resetZoom();
        syncAll(c);   //  FORCE BROADCAST AFTER RESET
      }
    });
  }

  function syncAll(chart) {
  handleZoom({ chart }); // reuse existing sync logic
  } 
    resetLinks.get(canvas).add(chart);
  }

// Cropshair and tooltip lonks
function linkHover(source, target) {
  if (!hoverLinks.has(source)) hoverLinks.set(source, new Set());
  hoverLinks.get(source).add(target);
}
const CrosshairPlugin = {
  id: 'crosshair',
  afterDraw(chart) {
    if (!chart._crosshair) return;

    const { ctx, chartArea } = chart;
    const { x, y } = chart._crosshair;

    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(200,200,200,0.6)';

    // Vertical
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();

    // Horizontal
    ctx.beginPath();
    ctx.moveTo(chartArea.left, y);
    ctx.lineTo(chartArea.right, y);
    ctx.stroke();

    ctx.restore();
  }
};

Chart.register(CrosshairPlugin);

function handleHover(event, sourceChart) {
  const sourceElements = sourceChart.getElementsAtEventForMode(
    event,
    'index',
    { intersect: false },
    false
  );

  // ✅ HARD GUARD — nothing hovered
  if (!sourceElements || sourceElements.length === 0) {
    clearHover(sourceChart);
    return;
  }

  const index = sourceElements[0].index;
  const xPixel = sourceElements[0].element.x;

  sourceChart._crosshair = { x: xPixel };
  sourceChart.tooltip.setActiveElements(sourceElements, { x: xPixel });

  const targets = hoverLinks.get(sourceChart);
  if (!targets) return;

  for (const target of targets) {
    syncTargetHover(target, index, xPixel);
  }

  sourceChart.draw();
}
function syncTargetHover(targetChart, index, xPixel) {
  const elements = [];

  targetChart.data.datasets.forEach((ds, di) => {
    if (ds.data && ds.data[index] && !isNaN(ds.data[index].y)) {
      elements.push({ datasetIndex: di, index });
    }
  });

  //  Prevents getLabelAndValue crash
  if (elements.length === 0) {
    targetChart.tooltip.setActiveElements([], { x: 0, y: 0 });
    targetChart._crosshair = null;
  } else {
    targetChart.tooltip.setActiveElements(elements, { x: xPixel });
    targetChart._crosshair = { x: xPixel };
  }

  targetChart.draw();
}
function clearHover(chart) {
  chart._crosshair = null;
  chart.tooltip.setActiveElements([], { x: 0, y: 0 });
  chart.draw();

  const targets = hoverLinks.get(chart);
  if (!targets) return;

  for (const t of targets) {
    t._crosshair = null;
    t.tooltip.setActiveElements([], { x: 0, y: 0 });
    t.draw();
  }
}

function attachCrosshair(chart) {
  const canvas = chart.canvas;

  canvas.addEventListener('mousemove', e => handleHover(e, chart));

  canvas.addEventListener('mouseleave', () => {
    chart._crosshair = null;
    chart.tooltip.setActiveElements([], { x: 0, y: 0 });
    chart.draw();

    const targets = hoverLinks.get(chart);
    if (!targets) return;

    for (const t of targets) {
      t._crosshair = null;
      t.tooltip.setActiveElements([], { x: 0, y: 0 });
      t.draw();
    }
  });
}
// Custom toltip positioner next to cursor
Chart.Tooltip.positioners.cursor = function(items, eventPosition) {
  return {
    x: eventPosition.x - 10,
    y: eventPosition.y + 10
  };
};
// ===== CHART GENERTATION=====
// Add data to the chart
function loadAll(candles) {
  for (let index = 0; index < candles.length; index++) {    
    const candle = candles[index];                
      createTitle(`Title_${candle.interval}`, `Candle interval ${candle.interval}`)

      const priceExtraCanvas  = createCanvas(candle.interval);
      const priceExtraChart = createCandleChart(priceExtraCanvas.id);
      priceExtraChart.data.datasets[0].data = candle.data;            
      
      const volumeExtraCanvas  = createCanvas(`${candle.interval}_volume`, 'solo_chart');
      const volumeExtraChart = createVolumeChart(volumeExtraCanvas.id);

      volumeExtraChart.data.datasets[0].data = candle.data.map(c => ({
        x: c.x,
        y: c.v,
        color: c.c >= c.o ? 'rgba(0,200,0,0.6)' : 'rgba(200,0,0,0.6)'
      }));  
      
      load_trades(priceExtraChart);
      load_avrages(priceExtraChart);

      load_integrated_indicators(integratedInd, priceExtraChart, candle.interval);
      load_solo_indicators(soloInd, priceExtraChart, priceExtraCanvas, candle.interval);
      
      // --- LINK PRICE ↔ VOLUME ---
      linkZoom(priceExtraChart, volumeExtraChart);
      linkZoom(volumeExtraChart, priceExtraChart);

      // --- APPLY HANDLERS ONCE ---
      priceExtraChart.options.plugins.zoom.zoom.onZoom = handleZoom;
      priceExtraChart.options.plugins.zoom.pan.onPan   = handleZoom;

      volumeExtraChart.options.plugins.zoom.zoom.onZoom = handleZoom;
      volumeExtraChart.options.plugins.zoom.pan.onPan   = handleZoom;

      // --- RESET ---
      attachResetZoom(priceExtraCanvas,  priceExtraChart);
      attachResetZoom(priceExtraCanvas,  volumeExtraChart);

      attachResetZoom(volumeExtraCanvas, volumeExtraChart);
      attachResetZoom(volumeExtraCanvas, priceExtraChart);

      // Link croshair
      linkHover(priceExtraChart, volumeExtraChart);
      linkHover(volumeExtraChart, priceExtraChart);

      attachCrosshair(priceExtraChart);
      attachCrosshair(volumeExtraChart);

      priceExtraChart.update();
      volumeExtraChart.update();    
  }
  

}

//Load trade data
function load_trades(chart){
  chart.data.datasets.push({
    type: 'scatter',
    label: tradeData.name,
    data: tradeData.data,
    pointRadius: 7,
    pointStyle: tradeData.data.map(t =>
      t.side === 'buy' ? 'triangle' : 'rectRot'
      ),
    pointBackgroundColor: tradeData.data.map(t =>
        t.side === 'buy' ? 'lime' : 'red'
      ),
    parsing: false
  });
}
//Load Avrages
function load_avrages(chart){
  for (let index = 0; index < avgs.length; index++) {
    let color = randomColor(index,2,2,1);
    chart.data.datasets.push({
      type: 'line',
      label: avgs[index].name,
      borderWidth: 1,
      pointRadius: 0,
      tension: 0.2,
      data: avgs[index].data,       
      borderColor: color,
      backgroundColor: color,   
      hidden: true,
      parsing: false
    });  
  }
}
//Load integrated indicators
function load_integrated_indicators(indicators, chart, interval){
  for (let index = 0; index < indicators.length; index++) {
    const element = indicators[index];
    if (element.interval === interval) {
      //console.log(element.type);
      let color = randomColor(10,10,10,1);
      switch (element.type) {
        case 'BB':
          const name = `${element.type} ${element.interval}`;           
          color = randomColor(1,0,20,1);          
          addIndicator(chart, element.name, element.data, color);
          break;
        case 'SMA':
        case 'EMA':          
          color = randomColor(50,1,1,1);          
          addIndicator(chart, element.name, element.data, color);
          break;
      
        default:
          color = randomColor(1,1,1,1);          
          addIndicator(chart, element.name, element.data, color);
          break;
      }
      chart.update();
    }
  }
}
//Load solo indicators
function load_solo_indicators(indicators, mainChart, mainCanvas, interval){
  for (let index = 0; index < indicators.length; index++) {
    const element = indicators[index];
    if (element.interval === interval) {      
      const priceIndicCanvas  = createCanvas(`solo_${element.name}_${interval}`, 'solo_chart');
      const priceIndicChart = createEmptyChart(priceIndicCanvas.id);      
      let color = randomColor(10,10,10,1);

      switch (element.type) {
        case 'RSI':
        case 'ADX':
          color = randomColor(0,1,3,1);
          addIndicator(priceIndicChart, element.name, element.data, color, false);
          priceIndicChart.options.scales.y.suggestedMin = 0;
          priceIndicChart.options.scales.y.suggestedMax = 100;
          break;
        case 'ROC':
          color = randomColor(0,0,5,1);
          addIndicator(priceIndicChart, element.name, element.data, color, false);
          break;

        case 'F&G':
          color = randomColor(10,6,0,1);
          addIndicator(priceIndicChart, element.name, element.data, color, false);
          priceIndicChart.options.scales.y.suggestedMin = 0;
          priceIndicChart.options.scales.y.suggestedMax = 100;      
          break;
        default:          
          addIndicator(priceIndicChart, element.name, element.data, color, false);
          break;
      }

      // --- BI-DIRECTIONAL LINK ---
      linkZoom(mainChart, priceIndicChart);
      linkZoom(priceIndicChart, mainChart);

      // --- APPLY HANDLERS ONCE ---
      mainChart.options.plugins.zoom.zoom.onZoom = handleZoom;
      mainChart.options.plugins.zoom.pan.onPan   = handleZoom;

      priceIndicChart.options.plugins.zoom.zoom.onZoom = handleZoom;
      priceIndicChart.options.plugins.zoom.pan.onPan   = handleZoom;

      // --- RESET ---
      attachResetZoom(mainCanvas, mainChart);
      attachResetZoom(mainCanvas, priceIndicChart);

      attachResetZoom(priceIndicCanvas, priceIndicChart);
      attachResetZoom(priceIndicCanvas, mainChart);
      //lionk croshair
      linkHover(mainChart, priceIndicChart);
      linkHover(priceIndicChart, mainChart);

      attachCrosshair(priceIndicChart);

      priceIndicChart.update();
    }
  }
}

loadAll(candleData);


function addIndicator(chart, name, data, color, hide = true) {  

  chart.data.datasets.push({
    label: name,
    type: 'line',
    data: data,
    borderColor: color,
    backgroundColor: color,
    hidden: hide,
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.2
  });

}

function randomColor(rk=1,gk=1,bk=1,alpha = 1) {
  const r = Math.min(Math.floor(Math.random() * 200 * rk + 30),255);
  const g = Math.min(Math.floor(Math.random() * 200 * gk + 30),255);
  const b = Math.min(Math.floor(Math.random() * 200 * bk + 30),255);

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function createCanvas(id,setClass = 'price_chart') {
  const container = document.getElementById('charts_div');

  const canvas = document.createElement('canvas');
  canvas.id = id;
  canvas.className= setClass;

  container.appendChild(canvas);

  return canvas;
}

function createTitle(id, text, type = 'h2', setClass = 'title') {
  const container = document.getElementById('charts_div');

  const title = document.createElement(type);
  title.innerText = text
  title.id = id;
  title.className= setClass;

  container.appendChild(title);

  return title;
}
