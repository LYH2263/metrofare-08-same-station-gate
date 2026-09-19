<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON } from '../api'
const route = useRoute()
const st = ref(null)
const load = async () => { st.value = await getJSON(`/api/stations/${route.params.code}`) }
onMounted(load); watch(() => route.params.code, load)
</script>
<template>
  <div class="page" v-if="st">
    <h1>{{ st.name }}</h1>
    <p class="muted">编码 {{ st.code }}</p>
    <p>
      <router-link :to="`/planner?from=${st.code}`">从本站试算 →</router-link>
      <span class="muted">（仅预填本站为起点，目的站需另行选择）</span>
    </p>
  </div>
</template>
