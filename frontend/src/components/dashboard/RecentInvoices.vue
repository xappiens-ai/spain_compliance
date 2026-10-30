<template>
  <div class="flex flex-col gap-1">
    <div
      v-if="!rows?.length"
      class="rounded-md bg-surface-gray-1 px-3 py-4 text-center text-p-sm text-ink-gray-5"
    >
      {{ __(emptyLabel) }}
    </div>
    <button
      v-for="row in rows"
      :key="row.name"
      type="button"
      class="flex items-center justify-between gap-3 rounded-md px-2 py-2 text-left transition hover:bg-surface-gray-1"
      @click="$emit('open', row.name)"
    >
      <div class="min-w-0">
        <div class="truncate text-base font-medium text-ink-gray-9">
          {{ row.name }}
        </div>
        <div class="truncate text-p-sm text-ink-gray-6">
          {{ row[partyKey] || '—' }}
          <span v-if="row.posting_date"> · {{ formatDate(row.posting_date) }}</span>
        </div>
      </div>
      <div class="shrink-0 text-end">
        <div class="text-base tabular-nums text-ink-gray-9">
          {{ formatMoney(row.grand_total) }}
        </div>
        <Badge
          v-if="row.status"
          :label="row.status"
          variant="subtle"
          :theme="statusTheme(row.status)"
        />
      </div>
    </button>
  </div>
</template>

<script setup>
import { Badge, dayjs } from 'frappe-ui'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  partyKey: { type: String, default: 'customer_name' },
  currency: { type: String, default: 'EUR' },
  emptyLabel: { type: String, default: 'Sin registros' },
})

defineEmits(['open'])

const formatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: props.currency || 'EUR',
  maximumFractionDigits: 2,
})

function formatMoney(value) {
  return formatter.format(Number(value) || 0)
}

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}

function statusTheme(status) {
  const v = String(status || '').toLowerCase()
  if (['paid', 'completed'].includes(v)) return 'green'
  if (['overdue', 'unpaid'].includes(v)) return 'red'
  if (['return', 'credit note issued'].includes(v)) return 'orange'
  return 'gray'
}
</script>
