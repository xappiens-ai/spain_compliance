<template>
  <div class="flex h-screen w-screen print:block print:h-auto print:w-auto">
    <AppSidebar class="print:hidden" />
    <div
      class="flex h-full flex-1 flex-col overflow-hidden bg-surface-base print:block print:h-auto print:overflow-visible"
    >
      <AppHeader class="print:hidden" />
      <main
        class="relative flex flex-1 flex-col overflow-auto print:block print:overflow-visible"
      >
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from '@/components/Layouts/AppSidebar.vue'
import AppHeader from '@/components/Layouts/AppHeader.vue'
</script>
