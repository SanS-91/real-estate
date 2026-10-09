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


  // A categorical project comparison must not connect independent properties into a
  // time-series curve. Render one floating vertical interval per project instead.
  function renderRangeSeries(id, { labels = [], lowValues = [], highValues = [], lowLabel = 'Giá thấp', highLabel = 'Giá cao', yFormatter = compactNumber } = {}) {
    const ranges = labels.map((_, i) => {
      const low = Number(lowValues[i]), high = Number(highValues[i]);
      return Number.isFinite(low) && Number.isFinite(high) && low > 0 && high >= low
        ? [low, high] : null;
    });
    return render(id, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Khoảng giá chào bán',
          data: ranges,
          backgroundColor: 'rgba(139,30,45,.28)',
          hoverBackgroundColor: 'rgba(139,30,45,.45)',
          borderColor: '#8b1e2d',
          borderWidth: 1.4,
          borderRadius: 3,
          borderSkipped: false,
          maxBarThickness: 24
        }]
      },
      options: {
        ...baseOptions({ yFormatter }),
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(context) {
                const range = context.raw;
                if (!Array.isArray(range)) return 'Chưa có khoảng giá';
                return `${lowLabel}: ${yFormatter(range[0])} · ${highLabel}: ${yFormatter(range[1])}`;
              }
            }
          }
        }
      }
    });
  }

  window.ChartTools = { render, destroy, renderSupplySales, renderPriceTrend, renderTimeSeries, renderRangeSeries };
})();
