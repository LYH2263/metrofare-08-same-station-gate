<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON } from '../api'
const route = useRoute()
const stations = ref([])
const start = ref('')
const end = ref('')
const out = ref(null)
const rejection = ref(null)

const nameOf = (code) => stations.value.find(s => s.code === code)?.name || code

onMounted(async () => {
  stations.value = (await getJSON('/api/stations')).items
  // 从站点详情“从本站试算”跳来：只预填起点，终点刻意留空，绝不预填本站。
  start.value = route.query.from || stations.value[0]?.code || ''
  end.value = ''
})

const run = async () => {
  out.value = null
  rejection.value = null
  if (!start.value || !end.value) {
    rejection.value = { error: 'incomplete', message: '请先选择起点站和目的站。' }
    return
  }
  // 同站进出闸：前端先行拦截，只展示拒绝原因，不展示票价卡，也不发起写入。
  if (start.value === end.value) {
    rejection.value = {
      error: 'same_station',
      message: `同站进出闸被拒绝：起点与终点都是「${nameOf(start.value)}」(${start.value})，不能发售零站车票。`,
    }
    return
  }
  try {
    out.value = await postJSON('/api/quote', { start: start.value, end: end.value, persist: true })
  } catch (e) {
    // 同站(same_station)与未知站(unknown_station)等后端拒绝：只显示原因，票价卡不出现。
    rejection.value = { error: e.data?.error || 'error', message: e.message }
  }
}
</script>
<template>
  <div class="page"><h1>最短站数票价</h1>
    <div class="panel">
      <select v-model="start">
        <option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }} ({{ s.code }})</option>
      </select>
      →
      <select v-model="end">
        <option value="" disabled>请选择目的站</option>
        <option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }} ({{ s.code }})</option>
      </select>
      <button @click="run">试算</button>
    </div>
    <!-- 拒绝原因：同站进出闸 / 未知站等。此时绝不渲染票价卡。 -->
    <div v-if="rejection" class="panel reject-box">
      <p class="reject-text">{{ rejection.message }}</p>
    </div>
    <!-- 合法的不同站：才展示站数与票价。 -->
    <div v-else-if="out" class="panel">
      <p v-if="out.reachable">站数 {{ out.hops }} · 票价 <span class="hero-num">¥{{ out.fare }}</span></p>
      <p v-else class="muted">两站之间暂不可达</p>
    </div>
  </div>
</template>
