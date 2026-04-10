<template>
  <div class="chart-wrapper">
    <div class="chart-header">
      <p class="chart-title">Sentiment wave</p>
      <div class="chart-legend">
        <span class="legend-dot" style="background:#1D9E75"></span><span class="legend-label">positive</span>
        <span class="legend-dot" style="background:#888"></span><span class="legend-label">neutral</span>
        <span class="legend-dot" style="background:#E24B4A"></span><span class="legend-label">negative</span>
      </div>
    </div>
    <canvas ref="chartRef" height="100" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip } from 'chart.js'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip)

const props = defineProps({
  ticks: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart = null

const buildChart = () => {
  if (chart) chart.destroy()
  const labels = props.ticks.map(t => `T${t.tick}`)
  chart = new Chart(chartRef.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'positive',
          data: props.ticks.map(t => t.positive ?? 0),
          borderColor: '#1D9E75',
          backgroundColor: 'rgba(29,158,117,0.08)',
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        },
        {
          label: 'neutral',
          data: props.ticks.map(t => t.neutral ?? 0),
          borderColor: '#555',
          backgroundColor: 'rgba(136,135,128,0.05)',
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        },
        {
          label: 'negative',
          data: props.ticks.map(t => t.negative ?? 0),
          borderColor: '#E24B4A',
          backgroundColor: 'rgba(226,75,74,0.08)',
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      animation: { duration: 400 },
      plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
      scales: {
        x: { grid: { color: '#1a1a1a' }, ticks: { color: '#444', font: { size: 11 } } },
        y: { min: 0, max: 1, grid: { color: '#1a1a1a' }, ticks: { color: '#444', font: { size: 11 } } }
      }
    }
  })
}

watch(() => props.ticks, buildChart, { deep: true })
onMounted(buildChart)
onUnmounted(() => { if (chart) chart.destroy() })
</script>

<style scoped>
.chart-wrapper {
  background: #111;
  border: 1px solid #1a1a1a;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chart-header { display: flex; justify-content: space-between; align-items: center; }
.chart-title { font-size: 12px; color: #555; }
.chart-legend { display: flex; align-items: center; gap: 12px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.legend-label { font-size: 11px; color: #444; margin-left: 4px; }
</style>