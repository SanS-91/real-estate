(() => {
  'use strict';

  const instances = new Map();

  function destroy(id) {
    const chart = instances.get(id);
    if (chart) chart.destroy();
    instances.delete(id);
  }

  function compactNumber(value) {
    return window.Formatters?.compact?.(value) ?? (value === null || value === undefined ? '—' : String(value));
  }

  function baseOptions({ yFormatter = compactNumber, percent = false } = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true } },
        tooltip: {
          callbacks: {
            label(context) {
              const value = context.parsed.y;
              const formatted = percent ? `${(value * 100).toFixed(0)}%` : yFormatter(value);
              return `${context.dataset.label}: ${formatted}`;
            }
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#667085' } },
        y: {
          beginAtZero: false,
          grid: { color: '#eef0f3' },
          ticks: { color: '#667085', callback: value => percent ? `${Math.round(value * 100)}%` : yFormatter(value) }
        }
      }
    };
  }

  function render(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === 'undefined') return null;
    destroy(id);
    const chart = new Chart(canvas, config);
    instances.set(id, chart);
    return chart;
  }

  function renderSupplySales(id, rows) {
    return render(id, {
      type: 'bar',
      data: {
        labels: rows.map(row => row.period),
        datasets: [
          { label: 'New Supply', data: rows.map(row => row.new_supply), backgroundColor: '#c9aeb4', borderRadius: 3 },
          { label: 'Sales', data: rows.map(row => row.sales_units), backgroundColor: '#8b1e2d', borderRadius: 3 }
        ]
      },
      options: baseOptions()
    });
  }

  function renderPriceTrend(id, series) {
    const palette = ['#8b1e2d', '#344054', '#7a6752', '#667085', '#a15c68'];
    const periods = [...new Set(series.flatMap(item => item.values.map(v => v.period)))].sort();
    const datasets = series.map((item, index) => ({
      label: item.label,
      data: periods.map(period => item.values.find(v => v.period === period)?.value ?? null),
      borderColor: palette[index % palette.length],
      backgroundColor: palette[index % palette.length],
      tension: .25,
      spanGaps: false,
      pointRadius: 3
    }));
    return render(id, {
      type: 'line',
      data: { labels: periods, datasets },
      options: baseOptions({ yFormatter: value => window.Formatters?.aspVndPerSqm?.(value, { short: true }) ?? `${(value / 1_000_000).toFixed(0)} mn` })
    });
  }


  function renderTimeSeries(id, { label, labels = [], values = [], yFormatter = compactNumber, stepped = false } = {}) {
    return render(id, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: label || 'Series',
          data: values,
          borderColor: '#8b1e2d',
          backgroundColor: '#8b1e2d',
          tension: stepped ? 0 : .22,
          stepped,
          spanGaps: false,
          pointRadius: values.length > 40 ? 0 : 2.5,
          pointHoverRadius: 4,
          borderWidth: 2
        }]
      },
      options: baseOptions({ yFormatter })
    });
  }


  function renderRangeSeries(id, { labels = [], lowValues = [], highValues = [], lowLabel = 'Lower bound', highLabel = 'Upper bound', yFormatter = compactNumber } = {}) {
    return render(id, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: lowLabel,
            data: lowValues,
            borderColor: '#667085',
            backgroundColor: '#667085',
            tension: .22,
            spanGaps: false,
            pointRadius: lowValues.length > 40 ? 0 : 2.5,
            pointHoverRadius: 4,
            borderWidth: 2
          },
          {
            label: highLabel,
            data: highValues,
            borderColor: '#8b1e2d',
            backgroundColor: '#8b1e2d',
            tension: .22,
            spanGaps: false,
            pointRadius: highValues.length > 40 ? 0 : 2.5,
            pointHoverRadius: 4,
            borderWidth: 2
          }
        ]
      },
      options: baseOptions({ yFormatter })
    });
  }

  window.ChartTools = { render, destroy, renderSupplySales, renderPriceTrend, renderTimeSeries, renderRangeSeries };
})();
