<template>
  <svg
    :viewBox="`0 0 100 ${alto}`"
    preserveAspectRatio="none"
    class="block w-full overflow-visible"
    :style="{ height: `${alto}px` }"
    aria-hidden="true"
  >
    <defs>
      <linearGradient :id="gradiente" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.28" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <line
      v-if="cero !== null"
      x1="0"
      x2="100"
      :y1="cero"
      :y2="cero"
      stroke="#CBD5E1"
      stroke-dasharray="2 2"
      stroke-width="1"
      vector-effect="non-scaling-stroke"
    />
    <path v-if="area" :d="area" :fill="`url(#${gradiente})`" />
    <path
      :d="linea"
      fill="none"
      :stroke="color"
      stroke-width="1.75"
      stroke-linejoin="round"
      stroke-linecap="round"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  valores: { type: Array, default: () => [] },
  color: { type: String, default: '#4F46E5' },
  alto: { type: Number, default: 32 },
  relleno: { type: Boolean, default: true },
})

const gradiente = `spark-${Math.random().toString(36).slice(2, 9)}`

const puntos = computed(() => {
  const valores = props.valores.map((v) => Number(v) || 0)
  if (valores.length < 2) return []
  const min = Math.min(...valores, 0)
  const max = Math.max(...valores, 0)
  const rango = max - min || 1
  const margen = 3
  return valores.map((valor, i) => ({
    x: (i / (valores.length - 1)) * 100,
    y: margen + (1 - (valor - min) / rango) * (props.alto - margen * 2),
  }))
})

const linea = computed(() =>
  puntos.value
    .map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(' '),
)

const cero = computed(() => {
  const valores = props.valores.map((v) => Number(v) || 0)
  if (!valores.some((v) => v < 0) || !valores.some((v) => v > 0)) return null
  const min = Math.min(...valores, 0)
  const max = Math.max(...valores, 0)
  return 3 + (1 - (0 - min) / (max - min || 1)) * (props.alto - 6)
})

const area = computed(() => {
  if (!props.relleno || !puntos.value.length) return ''
  const base = cero.value ?? props.alto
  const primero = puntos.value[0]
  const ultimo = puntos.value[puntos.value.length - 1]
  return `${linea.value} L${ultimo.x},${base} L${primero.x},${base} Z`
})
</script>
