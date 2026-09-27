<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-end justify-between gap-4">
      <div class="min-w-0">
        <div class="text-lg font-semibold tabular-nums text-ink-gray-9">
          {{ format(paid) }}
        </div>
        <div class="text-p-sm text-ink-gray-6">{{ __(paidLabel) }}</div>
      </div>
      <div class="min-w-0 text-end">
        <div class="text-lg font-semibold tabular-nums text-ink-gray-9">
          {{ format(unpaid) }}
        </div>
        <div class="text-p-sm text-ink-gray-6">{{ __(unpaidLabel) }}</div>
      </div>
    </div>
    <div class="relative h-2 overflow-hidden rounded-full bg-surface-gray-2">
      <div
        class="absolute inset-y-0 start-0 rounded-full transition-all"
        :class="barClass"
        :style="{ width: `${paidWidth}%` }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  paid: { type: Number, default: 0 },
  unpaid: { type: Number, default: 0 },
  currency: { type: String, default: 'EUR' },
  paidLabel: { type: String, default: 'Cobrado' },
  unpaidLabel: { type: String, default: 'Pendiente' },
  barTheme: { type: String, default: 'green' },
})

const total = computed(() => Number(props.paid) + Number(props.unpaid))

const paidWidth = computed(() => {
  if (!total.value) return 0
  return Math.min(100, Math.round((Number(props.paid) / total.value) * 100))
})

	const barClass = computed(() =>
  props.barTheme === 'orange' ? 'bg-amber-500' : 'bg-green-600',
)

const formatter = computed(
  () =>
    new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: props.currency || 'EUR',
      maximumFractionDigits: 2,
    }),
)

function format(value) {
  return formatter.value.format(Number(value) || 0)
}
</script>
