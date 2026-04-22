<script setup lang="ts">
const route = useRoute()

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Analysis', to: '/analysis' },
  { label: 'Resources', to: '/resources' },
  { label: 'Help', to: '/help' },
]
</script>

<template>
  <header class="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-100">
    <div class="max-w-[1400px] mx-auto h-16 flex items-center justify-between px-6">
      <NuxtLink to="/" class="text-xl font-bold text-primary no-underline">OmicsInferenceDeck</NuxtLink>
      <nav class="flex gap-2">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-all no-underline"
          :class="route.path === item.to
            ? 'bg-indigo-50 text-primary'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>
    </div>
  </header>
</template>
