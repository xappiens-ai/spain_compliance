<template>
  <div
    class="pointer-events-none absolute inset-x-0 bottom-0 top-6 flex flex-col items-center justify-center gap-4"
  >
    <div
      class="flex size-14 items-center justify-center rounded-full bg-surface-gray-1 p-4"
    >
      <component v-if="icon" :is="icon" class="size-6 text-ink-gray-6" />
    </div>
    <div class="flex flex-col items-center gap-1">
      <div class="text-base font-medium text-ink-gray-6">
        {{ __(title) }}
      </div>
      <div
        v-if="description"
        class="max-w-72 text-center text-p-sm text-ink-gray-5"
      >
        {{ __(description) }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
})
</script>
