<template>
  <Teleport to="#app-header" v-if="showHeader">
    <slot>
      <header class="flex h-12 items-center justify-between mx-4 md:ml-5 md:mr-0">
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <slot name="left-header" />
        </div>
        <div class="flex items-center gap-2 shrink-0 md:mr-5">
          <slot name="right-header" />
        </div>
      </header>
    </slot>
  </Teleport>
</template>

<script setup>
import { nextTick, ref } from 'vue'

const showHeader = ref(false)

nextTick(() => {
  showHeader.value = true
})
</script>
