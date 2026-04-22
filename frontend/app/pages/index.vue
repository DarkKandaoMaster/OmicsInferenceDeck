<script setup lang="ts">
useHead({ title: 'OmicsInferenceDeck' })
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh] text-center">
    <div>
      <h1 class="text-5xl font-extrabold text-slate-900 mb-4">多组学癌症亚型分析平台</h1>
      <p class="text-xl text-slate-500 mb-8">基于前沿算法与多组学数据，快速、精准识别癌症分子亚型</p>
      <NuxtLink
        to="/analysis"
        class="inline-block bg-gradient-to-r from-primary to-secondary text-white font-semibold text-lg px-10 py-4 rounded-full shadow-md hover:-translate-y-0.5 hover:shadow-lg transition-all no-underline"
      >
        开始分析之旅
      </NuxtLink>
    </div>
  </div>
</template>
