<template>
  <div
    class="flex min-w-0 flex-col gap-2 rounded-xl border border-outline-gray-1 bg-surface-elevation-1 p-4 print:break-inside-avoid"
  >
    <div class="flex items-start justify-between gap-2">
      <span class="text-sm font-medium text-ink-gray-5">{{ label }}</span>
      <component
        :is="icono"
        v-if="icono"
        class="size-4 shrink-0 text-ink-gray-4"
      />
    </div>
    <div
      class="truncate text-5xl font-semibold tabular-nums tracking-tight text-ink-gray-9"
      :title="titulo || valor"
    >
      {{ valor }}
    </div>
    <div class="flex min-h-5 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <Badge
        v-if="delta !== null && delta !== undefined && Number.isFinite(delta)"
        :label="textoDelta"
        :theme="temaDelta"
        variant="subtle"
      />
      <span v-if="deltaTexto" class="truncate text-ink-gray-5">{{
        deltaTexto
      }}</span>
    </div>
    <div v-if="pista" class="text-xs text-ink-gray-5">{{ pista }}</div>
    <Sparkline
      v-if="serie && serie.length > 1"
      :valores="serie"
      :color="color"
      :alto="34"
      class="mt-auto"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import Sparkline from '@/components/informes/Sparkline.vue'
import { formatPct } from '@/composables/informe'

const props = defineProps({
  label: { type: String, required: true },
  valor: { type: String, required: true },
  titulo: { type: String, default: '' },
  delta: { type: Number, default: null },
  deltaTexto: { type: String, default: '' },
  menosEsMejor: { type: Boolean, default: false },
  neutro: { type: Boolean, default: false },
  pista: { type: String, default: '' },
  serie: { type: Array, default: null },
  color: { type: String, default: '#4F46E5' },
  icono: { type: [Object, Function], default: null },
})

const textoDelta = computed(() => {
  const flecha = props.delta > 0 ? '↑' : props.delta < 0 ? '↓' : ''
  return `${flecha} ${formatPct(Math.abs(props.delta))}`.trim()
})

const temaDelta = computed(() => {
  if (props.neutro || !props.delta) return 'gray'
  const bueno = props.menosEsMejor ? props.delta < 0 : props.delta > 0
  return bueno ? 'green' : 'red'
})
</script>
