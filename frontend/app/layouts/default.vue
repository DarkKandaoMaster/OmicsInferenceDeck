<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'

const { registerUnloadHook } = useSession()
registerUnloadHook()
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 font-sans pb-15">
    <LayoutAppHeader />
    <main class="max-w-[1400px] mx-auto px-6">
      <slot />
    </main>
  </div>
</template>
