<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, getJSON, postJSON } from '../api'

const route = useRoute()
const stations = ref([])
// 从站点详情跳入时起点预填为该站;终点一律留空,绝不预填成起点站。
const start = ref(route.query.start || 'A1')
const end = ref(route.query.start ? '' : 'B2')
const out = ref(null)
const errorMsg = ref('')

onMounted(async () => { stations.value = (await getJSON('/api/stations')).items })

const run = async () => {
  out.value = null
  errorMsg.value = ''
  if (!end.value) {
    errorMsg.value = '请先选择终点站'
    return
  }
  // 选成同一站:本地直接拒绝,不请求、不展示票价卡。
  if (start.value === end.value) {
    errorMsg.value = `拒绝:起点与终点均为 ${start.value}(同站进出闸),无法出票`
    return
  }
  try {
    out.value = await postJSON('/api/quote', { start: start.value, end: end.value, persist: true })
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.message : String(e)
  }
}
</script>
<template>
  <div class="page"><h1>最短站数票价</h1>
    <div class="panel">
      <select v-model="start"><option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option></select>
      →
      <select v-model="end">
        <option value="" disabled>请选择终点</option>
        <option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option>
      </select>
      <button @click="run">试算</button>
    </div>
    <div v-if="errorMsg" class="panel reject">
      <p>⛔ {{ errorMsg }}</p>
    </div>
    <div v-else-if="out" class="panel">
      <p v-if="out.reachable">站数 {{ out.hops }} · 票价 <span class="hero-num">¥{{ out.fare }}</span></p>
      <p v-else class="muted">不可达</p>
    </div>
  </div>
</template>
