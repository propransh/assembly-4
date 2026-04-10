<template>
  <div class="sim-wrapper">
    <div class="sim-header">
      <div>
        <p class="sim-topic">{{ topic }}</p>
        <p class="sim-status">{{ statusText }}</p>
      </div>
      <div class="sim-controls">
        <button class="ctrl-btn" @click="togglePause">
          {{ paused ? 'Resume' : 'Pause' }}
        </button>
        <span class="tick-label">tick {{ currentTick }}</span>
        <button
  v-if="simulationDone"
  class="report-btn"
  @click="$router.push({ path: '/report', query: { topic: topic } })"
>
  View report →
</button>
      </div>
    </div>

    <div class="sim-body">
      <svg ref="svgRef" class="network-svg" />

      <div class="agent-panel" v-if="selectedAgent">
        <div class="panel-header">
          <div class="panel-avatar">{{ initials(selectedAgent.name) }}</div>
          <div>
            <p class="panel-name">{{ selectedAgent.name }}</p>
            <p class="panel-persona">{{ selectedAgent.persona }}</p>
          </div>
          <button class="close-btn" @click="selectedAgent = null">✕</button>
        </div>
        <div class="panel-stance" :class="`stance-${selectedAgent.stance}`">
          {{ selectedAgent.stance }}
        </div>
        <p class="panel-opinion">{{ selectedAgent.opinion }}</p>
        <div class="panel-messages">
          <p class="messages-label">Recent arguments</p>
          <div class="message" v-for="(msg, i) in selectedAgent.messages" :key="i">
            <span class="msg-from">{{ msg.from }}</span>
            <p class="msg-text">{{ msg.text }}</p>
          </div>
        </div>
      </div>
    </div>

    <SentimentChart :ticks="sentimentTicks" />
    <div class="live-feed">
      <p class="feed-label">Live feed</p>
      <div class="feed-messages">
        <div class="feed-msg" v-for="(msg, i) in feedMessages" :key="i">
          <span class="feed-agent" :style="{ color: msg.color }">{{ msg.agent }}</span>
          <span class="feed-text">{{ msg.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as d3 from 'd3'
import SentimentChart from './SentimentChart.vue'

const props = defineProps({
  topic: { type: String, default: 'Should AI be regulated by governments?' },
  agentCount: { type: Number, default: 12 },
  rounds: { type: Number, default: 3 }
})

const svgRef = ref(null)
const selectedAgent = ref(null)
const currentTick = ref(0)
const paused = ref(false)
const simulationDone = ref(false)
const feedMessages = ref([])
const sentimentTicks = ref([])

const stanceColors = {
  for: '#1D9E75',
  against: '#E24B4A',
  neutral: '#888780'
}

const personas = [
  { name: 'The Skeptic', persona: 'Analytical, hard to convince', stance: 'against' },
  { name: 'The Optimist', persona: 'Sees the best in everything', stance: 'for' },
  { name: 'The Realist', persona: 'Data-driven, cautious', stance: 'neutral' },
  { name: 'The Contrarian', persona: 'Challenges every assumption', stance: 'against' },
  { name: 'The Idealist', persona: 'Believes in a better world', stance: 'for' },
  { name: 'The Pragmatist', persona: 'Focuses on what works', stance: 'neutral' },
  { name: 'The Philosopher', persona: 'Questions everything deeply', stance: 'neutral' },
  { name: 'The Activist', persona: 'Passionate about change', stance: 'for' },
  { name: 'The Conservative', persona: 'Values tradition and stability', stance: 'against' },
  { name: 'The Futurist', persona: 'Excited about what is coming', stance: 'for' },
  { name: 'The Critic', persona: 'Finds flaws in every argument', stance: 'against' },
  { name: 'The Mediator', persona: 'Seeks common ground always', stance: 'neutral' },
]

const arguments_pool = {
  for: [
    'Regulation protects citizens from AI harm.',
    'Without oversight, AI will be weaponized.',
    'Every powerful technology needs governance.',
    'Look at social media — we waited too long.',
  ],
  against: [
    'Regulation will stifle innovation.',
    'Governments do not understand AI well enough.',
    'The market will self-correct naturally.',
    'Over-regulation kills competitive advantage.',
  ],
  neutral: [
    'We need more data before deciding.',
    'Both sides have valid points here.',
    'Context matters more than broad rules.',
    'Let us look at what other countries do first.',
  ]
}

const agents = ref([])
let simulation = null
let tickInterval = null
let svg, g, link, node

const initials = (name) => {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

const statusText = computed(() => {
  const forCount = agents.value.filter(a => a.stance === 'for').length
  const againstCount = agents.value.filter(a => a.stance === 'against').length
  const neutralCount = agents.value.filter(a => a.stance === 'neutral').length
  return `For: ${forCount} · Against: ${againstCount} · Neutral: ${neutralCount}`
})

const addFeedMessage = (agent, text) => {
  feedMessages.value.unshift({
    agent: agent.name,
    text,
    color: stanceColors[agent.stance]
  })
  if (feedMessages.value.length > 20) feedMessages.value.pop()
}

const runTick = () => {
  if (paused.value) return
  currentTick.value++

  agents.value.forEach(agent => {
    const others = agents.value.filter(a => a.id !== agent.id)
    const target = others[Math.floor(Math.random() * others.length)]

    if (Math.random() > 0.6) {
      const pool = arguments_pool[agent.stance]
      const argument = pool[Math.floor(Math.random() * pool.length)]
      addFeedMessage(agent, argument)
      agent.messages.unshift({ from: agent.name, text: argument })
      if (agent.messages.length > 5) agent.messages.pop()

      if (Math.random() > 0.75) {
        const stances = ['for', 'against', 'neutral']
        const newStance = stances[Math.floor(Math.random() * stances.length)]
        agent.stance = newStance
        agent.opinion = arguments_pool[newStance][0]
      }
    }
  })

  updateNodeColors()
  sentimentTicks.value.push({
  tick: currentTick.value,
  positive: agents.value.filter(a => a.stance === 'for').length / agents.value.length,
  neutral: agents.value.filter(a => a.stance === 'neutral').length / agents.value.length,
  negative: agents.value.filter(a => a.stance === 'against').length / agents.value.length
})
}

const updateNodeColors = () => {
  if (!node) return
  node.select('circle')
    .transition()
    .duration(400)
    .attr('fill', d => stanceColors[d.stance])
}

const togglePause = () => {
  paused.value = !paused.value
}

onMounted(() => {
  const count = Math.min(props.agentCount, personas.length)
  agents.value = personas.slice(0, count).map((p, i) => ({
    id: i,
    ...p,
    opinion: arguments_pool[p.stance][0],
    messages: [],
    x: 0, y: 0
  }))

  const el = svgRef.value
  const width = el.clientWidth || 700
  const height = el.clientHeight || 500

  svg = d3.select(el)
    .attr('width', width)
    .attr('height', height)

  g = svg.append('g')

  const links = []
  agents.value.forEach((a, i) => {
    const connectTo = Math.floor(Math.random() * agents.value.length)
    if (connectTo !== i) links.push({ source: i, target: connectTo })
  })

  simulation = d3.forceSimulation(agents.value)
    .force('link', d3.forceLink(links).id(d => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(40))

  link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#222')
    .attr('stroke-width', 1)

  node = g.append('g')
    .selectAll('g')
    .data(agents.value)
    .join('g')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null; d.fy = null
      })
    )
    .on('click', (event, d) => { selectedAgent.value = d })

  node.append('circle')
    .attr('r', 20)
    .attr('fill', d => stanceColors[d.stance])
    .attr('stroke', '#0a0a0a')
    .attr('stroke-width', 2)

  node.append('text')
    .text(d => initials(d.name))
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', '#fff')
    .attr('font-size', '11px')
    .attr('pointer-events', 'none')

  node.append('title').text(d => d.name)

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  tickInterval = setInterval(() => {
  if (currentTick.value >= props.rounds * 5) {
    clearInterval(tickInterval)
    simulationDone.value = true
    return
  }
  runTick()
}, 1800)
})

onUnmounted(() => {
  if (tickInterval) clearInterval(tickInterval)
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.sim-wrapper { display: flex; flex-direction: column; gap: 16px; padding: 20px; background: #0a0a0a; box-sizing: border-box; }
.sim-header { display: flex; justify-content: space-between; align-items: flex-start; }
.sim-topic { font-size: 16px; font-weight: 500; color: #fff; }
.sim-status { font-size: 12px; color: #555; margin-top: 4px; }
.sim-controls { display: flex; align-items: center; gap: 12px; }
.ctrl-btn { background: #111; border: 1px solid #2a2a2a; color: #aaa; padding: 6px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; }
.tick-label { font-size: 12px; color: #333; }
.sim-body { display: flex; gap: 16px; flex: 1; min-height: 0; }
.network-svg { flex: 1; background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 16px; height: 450px; }

.agent-panel { width: 280px; background: #111; border: 1px solid #1e1e1e; border-radius: 16px; padding: 20px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
.panel-header { display: flex; align-items: center; gap: 10px; }
.panel-avatar { width: 36px; height: 36px; border-radius: 50%; background: #1e1e1e; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 500; color: #aaa; flex-shrink: 0; }
.panel-name { font-size: 14px; font-weight: 500; color: #fff; margin: 0; }
.panel-persona { font-size: 11px; color: #555; margin: 2px 0 0; }
.close-btn { margin-left: auto; background: none; border: none; color: #555; cursor: pointer; font-size: 14px; }
.panel-stance { display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.stance-for { background: #0a2e1e; color: #1D9E75; }
.stance-against { background: #2e0a0a; color: #E24B4A; }
.stance-neutral { background: #1e1e1e; color: #888; }
.panel-opinion { font-size: 13px; color: #bbb; line-height: 1.6; }
.panel-messages { display: flex; flex-direction: column; gap: 8px; }
.messages-label { font-size: 11px; color: #444; }
.message { background: #0f0f0f; border-radius: 8px; padding: 8px 10px; }
.msg-from { font-size: 10px; color: #444; display: block; margin-bottom: 3px; }
.msg-text { font-size: 12px; color: #888; margin: 0; line-height: 1.5; }

.live-feed { background: #111; border: 1px solid #1a1a1a; border-radius: 12px; padding: 14px 16px; max-height: 140px; overflow: hidden; }
.feed-label { font-size: 11px; color: #444; margin-bottom: 8px; }
.feed-messages { display: flex; flex-direction: column; gap: 4px; }
.feed-msg { font-size: 12px; display: flex; gap: 8px; }
.feed-agent { font-weight: 500; white-space: nowrap; }
.feed-text { color: #555; }
</style>