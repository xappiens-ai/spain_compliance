<template>
  <div class="flex h-screen w-screen">
    <AppSidebar />
    <div class="flex flex-1 flex-col h-full overflow-hidden bg-surface-base">
      <AppHeader />
      <main class="flex flex-1 flex-col overflow-auto relative">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from '@/components/Layouts/AppSidebar.vue'
import AppHeader from '@/components/Layouts/AppHeader.vue'
</script>
