<template>
  <section
    class="flex min-w-0 flex-col rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:break-inside-avoid"
  >
    <header
      v-if="titulo || $slots.acciones"
      class="flex flex-wrap items-start justify-between gap-3 px-4 pt-4 sm:px-5"
    >
      <div class="min-w-0">
        <h3 class="text-xl font-semibold text-ink-gray-9">{{ titulo }}</h3>
        <p v-if="subtitulo" class="mt-1 text-sm text-ink-gray-5">
          {{ subtitulo }}
        </p>
      </div>
      <div v-if="$slots.acciones" class="flex items-center gap-2 print:hidden">
        <slot name="acciones" />
      </div>
    </header>
    <div
      class="flex min-h-0 flex-1 flex-col"
      :class="sinRelleno ? '' : 'p-4 sm:p-5'"
    >
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  titulo: { type: String, default: '' },
  subtitulo: { type: String, default: '' },
  sinRelleno: { type: Boolean, default: false },
})
</script>
