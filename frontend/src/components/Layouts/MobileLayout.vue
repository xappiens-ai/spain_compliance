<template>
  <div class="flex h-screen w-screen flex-col bg-surface-base">
    <div
      class="flex items-center gap-2 border-b border-outline-gray-1 px-3 py-2"
    >
      <Button variant="ghost" icon="lucide-menu" @click="showSidebar = true" />
      <div class="text-base font-medium text-ink-gray-9">
        {{ __('Contabilidad') }}
      </div>
    </div>
    <div v-if="showSidebar" class="fixed inset-0 z-40 flex">
      <div class="absolute inset-0 bg-black/40" @click="showSidebar = false" />
      <div class="relative z-10 h-full">
        <AppSidebar mobile @navigate="showSidebar = false" />
      </div>
    </div>
    <div class="flex border-b border-outline-gray-1">
      <div id="app-header" class="flex-1 w-full"></div>
    </div>
    <main class="flex flex-1 flex-col overflow-auto relative">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Button } from 'frappe-ui'
import AppSidebar from '@/components/Layouts/AppSidebar.vue'

const showSidebar = ref(false)
</script>
