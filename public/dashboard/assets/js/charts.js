/**
 * charts.js — Chart.js rendering for Pantausentimen dashboard.
 * Timeline, sentiment doughnut, distribution bars, word cloud.
 * Loaded before dashboard.js. Uses window.UI for formatters.
 */

(() => {
  "use strict";

  const SENTIMENT_COLORS = {
    positive: "#059669", negative: "#DC2626", neutral: "#64748B", unknown: "#CBD5E1",
  };
  const SENTIMENT_LABELS = {
    positive: "Positif", negative: "Negatif", neutral: "Netral", unknown: "Tidak Diketahui",
  };
  const DIST_BAR_COLORS = {
    positive: "#059669", negative: "#DC2626", neutral: "#64748B",
    pro: "#2563EB", contra: "#DC2626", netral: "#64748B",
    supportive: "#059669", critical: "#DC2626",
    questioning: "#D97706", informational: "#0891B2",
    call_to_action: "#7C3AED", boycott: "#DC2626", support: "#059669",
  };

  const chartRefs = { timeline: null, sentiment: null, realtime: null };

  function chartBaseOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 11, family: "Inter" }, padding: 14, usePointStyle: true, boxWidth: 8, boxHeight: 8 },
        },
        tooltip: {
          backgroundColor: "#1E293B",
          titleFont: { size: 12, family: "Inter", weight: "600" },
          bodyFont: { size: 11, family: "Inter" },
          padding: 10, cornerRadius: 8, displayColors: true, boxPadding: 4,
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 }, color: "#94A3B8" } },
        y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)", drawBorder: false }, ticks: { font: { size: 11 }, color: "#94A3B8" } },
      },
      animation: { duration: 700, easing: "easeOutQuart" },
      interaction: { intersect: false, mode: "index" },
    };
  }

  function renderTimelineChart(data) {
    const canvas = UI.$("timelineChart");
    if (!canvas) return;

    if (chartRefs.timeline) { chartRefs.timeline.destroy(); chartRefs.timeline = null; }

    const sentimentByDay = data.sentiment_by_day || {};
    const days = Object.keys(sentimentByDay).sort();

    if (days.length === 0) {
      const timeline = data.timeline || [];
      if (timeline.length === 0) {
        canvas.parentElement.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div>
            <div class="empty-state-title">Belum ada data timeline</div>
            <div class="empty-state-desc">Jalankan crawl untuk mulai mengumpulkan komentar.</div>
          </div>`;
        return;
      }

      chartRefs.timeline = new Chart(canvas, {
        type: "bar",
        data: { labels: timeline.map(r => r.day), datasets: [{ label: "Komentar", data: timeline.map(r => r.count), backgroundColor: "rgba(37, 99, 235, 0.85)", borderRadius: 6, borderSkipped: false, maxBarThickness: 36 }] },
        options: chartBaseOptions(),
      });
      return;
    }

    const sentimentKeys = ["positive", "neutral", "negative"];
    const datasets = sentimentKeys.map(s => ({
      label: SENTIMENT_LABELS[s],
      data: days.map(d => (sentimentByDay[d] || {})[s] || 0),
      backgroundColor: SENTIMENT_COLORS[s],
      borderRadius: 4, maxBarThickness: 36,
    }));

    chartRefs.timeline = new Chart(canvas, {
      type: "bar",
      data: { labels: days, datasets },
      options: {
        ...chartBaseOptions(),
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 }, color: "#94A3B8", maxRotation: 45 } },
          y: { stacked: true, beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)", drawBorder: false }, ticks: { font: { size: 11 }, color: "#94A3B8" } },
        },
      },
    });
  }

  function renderSentimentChart(distData) {
    const canvas = UI.$("sentimentChart");
    const legendWrap = UI.$("sentimentLegend");
    if (!canvas) return;

    if (chartRefs.sentiment) { chartRefs.sentiment.destroy(); chartRefs.sentiment = null; }

    const sentimentDist = distData.sentiment || {};
    const keys = Object.keys(sentimentDist);
    if (keys.length === 0) {
      canvas.parentElement.innerHTML = `<div class="empty-state"><div class="empty-state-title">Belum ada distribusi sentimen</div></div>`;
      return;
    }

    const total = Object.values(sentimentDist).reduce((a, b) => a + b, 0);
    const labels = keys.map(k => SENTIMENT_LABELS[k] || UI.capitalize(k));
    const values = keys.map(k => sentimentDist[k]);
    const colors = keys.map(k => SENTIMENT_COLORS[k] || "#CBD5E1");

    chartRefs.sentiment = new Chart(canvas, {
      type: "doughnut",
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: "#fff", hoverOffset: 4, spacing: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "70%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1E293B", bodyFont: { size: 12, family: "Inter" }, padding: 10, cornerRadius: 8,
            callbacks: { label(ctx) { return ` ${ctx.label}: ${ctx.parsed} (${((ctx.parsed / total) * 100).toFixed(1)}%)`; } },
          },
        },
        animation: { animateRotate: true, duration: 700 },
      },
      plugins: [{
        id: 'centerText',
        beforeDraw(chart) {
          const { ctx, width, height } = chart;
          ctx.save();
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.font = '600 10px Inter'; ctx.fillStyle = '#64748B';
          ctx.fillText('TOTAL DATA', width / 2, height / 2 - 8);
          ctx.font = 'bold 20px Inter'; ctx.fillStyle = '#0F172A';
          ctx.fillText(UI.formatNumber(total), width / 2, height / 2 + 10);
          ctx.restore();
        }
      }],
    });

    if (legendWrap) {
      legendWrap.innerHTML = `
        <div class="sentiment-legend-list">
          ${keys.map((k, i) => {
            const pct = total > 0 ? ((values[i] / total) * 100).toFixed(1) : 0;
            return `
              <div class="sentiment-legend-item">
                <div class="sentiment-legend-left">
                  <span class="sentiment-legend-dot" style="background:${colors[i]}"></span>
                  <span class="sentiment-legend-label">${SENTIMENT_LABELS[k] || UI.capitalize(k)}</span>
                </div>
                <div class="sentiment-legend-right">
                  <span class="sentiment-legend-value">${UI.formatNumber(values[i])}</span>
                  <span class="sentiment-legend-pct">(${pct}%)</span>
                </div>
              </div>`;
          }).join("")}
        </div>`;
    }
  }

  function renderDistBars(containerId, data, colorMap) {
    const wrap = UI.$(containerId);
    if (!wrap) return;

    const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
    const total = entries.reduce((s, [, v]) => s + v, 0);

    if (entries.length === 0) {
      wrap.innerHTML = `<div class="empty-state"><div class="empty-state-title">Belum ada data</div></div>`;
      return;
    }

    const maxVal = entries[0][1];

    wrap.innerHTML = entries.map(([label, count]) => {
      const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
      const barWidth = maxVal > 0 ? Math.max((count / maxVal) * 100, 2) : 0;
      const color = colorMap[label.toLowerCase()] || "#94A3B8";
      return `
        <div class="dist-bar">
          <div class="dist-bar-label">${UI.capitalize(label)}</div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width:${barWidth}%;background:${color};"></div>
          </div>
          <div class="dist-bar-value">${count} (${pct}%)</div>
        </div>`;
    }).join("");
  }

  function renderWordCloud(distData) {
    const wrap = UI.$("wordCloudContainer");
    const emptyState = UI.$("wordCloudEmpty");
    const canvas = UI.$("wordCloudCanvas");
    const hoverBox = UI.$("wordCloudHoverBox");
    
    if (!wrap || !canvas) return;

    const wordMap = {};
    const addWords = (obj) => {
      Object.entries(obj || {}).forEach(([k, v]) => {
        if (k && k !== "unknown" && k !== "null") {
          wordMap[k.toLowerCase()] = (wordMap[k.toLowerCase()] || 0) + v;
        }
      });
    };
    addWords(distData.issue); addWords(distData.stance); addWords(distData.action_intent);

    const entries = Object.entries(wordMap).sort((a, b) => b[1] - a[1]);
    
    if (entries.length === 0) {
      emptyState.style.display = "flex";
      emptyState.innerHTML = `<div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/></svg></div><div class="empty-state-title">Belum ada kata untuk ditampilkan</div><div class="empty-state-desc">Data word cloud akan muncul setelah inference selesai.</div>`;
      canvas.style.display = "none";
      if (hoverBox) hoverBox.hidden = true;
      return;
    }

    emptyState.style.display = "none";
    canvas.style.display = "block";

    // Prepare data for WordCloud (array of [word, count])
    const words = entries.map(([word, count]) => [UI.capitalize(word), count]);
    const maxCount = entries.length > 0 ? entries[0][1] : 1;

    // We store the original words to retrieve exact counts like in your example
    const originalWords = words.map(x => ({ word: x[0], count: x[1] }));

    if (window.WordCloud && window.WordCloud.isSupported) {
      // Define a custom color palette matching the dashboard theme
      const colorPalette = ["#2563EB", "#0891B2", "#059669", "#7C3AED", "#4F46E5", "#0F766E", "#BE185D", "#D97706"];
      
      const options = {
        list: words,
        gridSize: Math.round(16 * canvas.width / 1024),
        weightFactor: function (size) {
          // Increase scaling impact: largest words are much larger
          return (size / maxCount) * 75 + 12;
        },
        fontFamily: "'Inter', sans-serif",
        fontWeight: "bold",
        color: function() {
          return colorPalette[Math.floor(Math.random() * colorPalette.length)];
        },
        rotateRatio: 0.35, // 35% chance for a word to be rotated
        rotationSteps: 2, // Rotate to exactly 90 degrees
        shape: "circle",
        ellipticity: 0.65,
        shrinkToFit: true,
        minSize: 10,
        drawOutOfBound: false,
        classes: 'word-cloud-item',
        hover: (item, dimension, event) => {
          if (!hoverBox) return;
          if (!item) {
            hoverBox.style.opacity = "0";
            setTimeout(() => { if(hoverBox.style.opacity === "0") hoverBox.hidden = true; }, 200);
            canvas.style.cursor = "default";
            return;
          }
          canvas.style.cursor = "pointer";
          const originalItem = originalWords.find(x => x.word === item[0]);
          const count = originalItem ? originalItem.count : item[1];
          
          hoverBox.hidden = false;
          hoverBox.style.opacity = "1";
          hoverBox.innerHTML = `<span style="color: #64748B; font-weight: 500;">Kata:</span> ${item[0]}<br><span style="color: #64748B; font-weight: 500;">Frekuensi:</span> ${count}`;
          
          // Position tooltip exactly near the mouse cursor for a sleek feel
          if (event) {
            hoverBox.style.left = (event.offsetX + 15) + 'px';
            hoverBox.style.top = (event.offsetY + 15) + 'px';
            hoverBox.style.transform = 'none'; // Override previous transform
            hoverBox.style.marginTop = '0';
          }
        },
        click: (item, dimension, event) => {
          // Click handler from your example
          const originalItem = originalWords.find(x => x.word === item[0]);
          const count = originalItem ? originalItem.count : item[1];
          if (window.UI && window.UI.showToast) {
            window.UI.showToast("info", item[0], `Disebutkan ${count} kali`);
          } else {
            alert(`${item[0]}: ${count}`);
          }
        }
      };

      // Handle hover box hiding when mouse leaves the canvas
      canvas.addEventListener("mouseleave", () => {
        if (hoverBox) hoverBox.hidden = true;
      });

      WordCloud(canvas, options);
    } else {
      emptyState.style.display = "flex";
      emptyState.innerHTML = `<div class="empty-state-title">WordCloud tidak disupport di browser ini.</div>`;
      canvas.style.display = "none";
    }
  }

  // =========================================================================
  // Real-time Monitoring Line Chart
  // =========================================================================

  function initRealtimeChart() {
    const canvas = UI.$("realtimeMonitorChart");
    if (!canvas) return null;

    if (chartRefs.realtime) { chartRefs.realtime.destroy(); chartRefs.realtime = null; }

    chartRefs.realtime = new Chart(canvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Komentar Masuk",
            data: [],
            borderColor: "#2563EB",
            backgroundColor: "rgba(37, 99, 235, 0.12)",
            borderWidth: 2, tension: 0.35, fill: true,
            pointRadius: 2, pointHoverRadius: 4,
          },
          {
            label: "Selesai Dianalisis",
            data: [],
            borderColor: "#059669",
            backgroundColor: "rgba(5, 150, 105, 0.10)",
            borderWidth: 2, tension: 0.35, fill: true,
            pointRadius: 2, pointHoverRadius: 4,
          },
        ],
      },
      options: {
        ...chartBaseOptions(),
        animation: { duration: 300 },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, color: "#94A3B8", maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
          y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)", drawBorder: false }, ticks: { font: { size: 11 }, color: "#94A3B8", precision: 0 } },
        },
      },
    });
    return chartRefs.realtime;
  }

  function updateRealtimeChart(data) {
    const chart = chartRefs.realtime || initRealtimeChart();
    if (!chart || !data) return;

    const datasets = data.datasets || {};
    chart.data.labels = data.labels || [];
    chart.data.datasets[0].data = datasets.ingested || [];
    chart.data.datasets[1].data = datasets.inferred || [];
    chart.update();
  }

  // Expose globally
  window.Charts = {
    SENTIMENT_COLORS, SENTIMENT_LABELS, DIST_BAR_COLORS,
    chartRefs, renderTimelineChart, renderSentimentChart,
    renderDistBars, renderWordCloud,
    initRealtimeChart, updateRealtimeChart,
  };
})();
