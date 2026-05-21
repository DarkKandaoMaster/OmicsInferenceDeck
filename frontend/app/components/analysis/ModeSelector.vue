<script setup lang="ts">
const isCustomEvalMode = defineModel<boolean>('isCustomEvalMode', { required: true })
</script>

<template>
  <div class="contents">
    <section class="mx-auto grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
      <label
        class="flex min-h-[74px] cursor-pointer items-center justify-between rounded-lg border bg-white px-5 py-4 shadow-sm transition-all hover:border-primary"
        :class="isCustomEvalMode ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-800'"
      >
        <input v-model="isCustomEvalMode" type="radio" :value="true" class="sr-only" />
        <span class="text-sm font-semibold">我想测试自己的算法</span>
        <span class="h-4 w-4 rounded-full border" :class="isCustomEvalMode ? 'border-primary bg-primary' : 'border-slate-300'" />
      </label>

      <label
        class="flex min-h-[74px] cursor-pointer items-center justify-between rounded-lg border bg-white px-5 py-4 shadow-sm transition-all hover:border-primary"
        :class="!isCustomEvalMode ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-800'"
      >
        <input v-model="isCustomEvalMode" type="radio" :value="false" class="sr-only" />
        <span class="text-sm font-semibold">我想测试平台内置算法</span>
        <span class="h-4 w-4 rounded-full border" :class="!isCustomEvalMode ? 'border-primary bg-primary' : 'border-slate-300'" />
      </label>
    </section>

    <section class="mx-auto grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
      <label class="flex min-h-[74px] cursor-default items-center justify-between rounded-lg border border-primary bg-indigo-50 px-5 py-4 text-primary shadow-sm">
        <span class="text-sm font-semibold">我想测试无监督学习</span>
        <span class="h-4 w-4 rounded-full border border-primary bg-primary" />
      </label>

      <label class="flex min-h-[74px] cursor-not-allowed items-center justify-between rounded-lg border border-slate-200 bg-slate-100 px-5 py-4 text-slate-400">
        <input type="radio" disabled class="sr-only" />
        <span class="text-sm font-semibold">我想测试监督学习（暂未开放）</span>
        <span class="h-4 w-4 rounded-full border border-slate-300" />
      </label>
    </section>
  </div>
</template>
