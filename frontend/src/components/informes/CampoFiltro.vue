<template>
  <div class="flex flex-col gap-1.5">
    <span class="text-xs font-medium text-ink-gray-5">{{ label }}</span>
    <div class="flex min-h-7 items-center">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
})
</script>
