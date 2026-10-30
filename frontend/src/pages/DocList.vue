<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __(title), route: $route.fullPath }]" />
    </template>
    <template #right-header>
      <Button
        v-if="deskPath"
        :label="buttonLabel"
        theme="gray"
        variant="solid"
        @click="openInDesk()"
      >
        <template #prefix>
          <LucidePlus class="size-4" />
        </template>
      </Button>
    </template>
  </LayoutHeader>

  <ListViewBuilder :options="listOptions">
    <template #cell="{ column, item }">
      <Badge
        v-if="column.key === 'docstatus'"
        :label="docstatusLabel(item)"
        :theme="docstatusTheme(item)"
        variant="subtle"
      />
      <Badge
        v-else-if="column.key === 'status' && typeof item === 'string'"
        :label="item"
        :theme="statusTheme(item)"
        variant="subtle"
      />
      <span
        v-else-if="isMoneyColumn(column.key)"
        class="truncate text-base tabular-nums"
      >
        {{ formatAmount(item) }}
      </span>
      <span v-else-if="isDateColumn(column.key)" class="truncate text-base">
        {{ formatDate(item) }}
      </span>
      <span v-else class="truncate text-base">{{ item }}</span>
    </template>
  </ListViewBuilder>
</template>

<script setup>
import { computed } from 'vue'
import { Badge, Breadcrumbs, Button, dayjs } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ListViewBuilder from '@/components/ListViewBuilder.vue'
import LucidePlus from '~icons/lucide/plus'
import LucideBox from '~icons/lucide/box'

const props = defineProps({
  title: { type: String, required: true },
  doctype: { type: String, required: true },
  deskPath: { type: String, default: '' },
  newLabel: { type: String, default: '' },
  fields: { type: Array, default: () => ['name'] },
  columns: { type: Array, default: () => [] },
  filters: { type: Object, default: () => ({}) },
  orderBy: { type: String, default: 'modified desc' },
  emptyTitle: { type: String, default: '' },
  emptyDescription: { type: String, default: '' },
})

const moneyKeys = new Set([
  'grand_total',
  'rounded_total',
  'paid_amount',
  'received_amount',
  'total_debit',
  'outstanding_amount',
  'base_grand_total',
])

const dateKeys = new Set([
  'posting_date',
  'transaction_date',
  'due_date',
  'valid_till',
])

const listOptions = computed(() => ({
  doctype: props.doctype,
  rowKey: 'name',
  fields: props.fields,
  filters: props.filters,
  orderBy: props.orderBy,
  pageLength: 20,
  columns: props.columns,
  onRowClick: (row) => openInDesk(row.name),
  emptyState: {
    title: props.emptyTitle || __('Sin registros'),
    description:
      props.emptyDescription || __('No hay documentos para mostrar en ERPNext'),
  },
  emptyStateIcon: LucideBox,
}))

const buttonLabel = computed(() => props.newLabel || __('Nuevo'))

function isMoneyColumn(key) {
  return moneyKeys.has(key)
}

function isDateColumn(key) {
  return dateKeys.has(key)
}

function docstatusLabel(value) {
  return { 0: __('Borrador'), 1: __('Validado'), 2: __('Cancelado') }[value] ?? value
}

function docstatusTheme(value) {
  return { 0: 'gray', 1: 'green', 2: 'red' }[value] ?? 'gray'
}

function statusTheme(value) {
  const v = String(value).toLowerCase()
  if (['paid', 'submitted', 'completed', 'return'].includes(v)) return 'green'
  if (['overdue', 'cancelled', 'canceled', 'unpaid'].includes(v)) return 'red'
  if (['draft', 'cancelled'].includes(v)) return 'gray'
  return 'blue'
}

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}

const currencyFormat = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
})

function formatAmount(value) {
  return typeof value === 'number' ? currencyFormat.format(value) : value
}

function openInDesk(name) {
  if (!props.deskPath) return
  const base = `/app/${props.deskPath}`
  window.open(name ? `${base}/${name}` : `${base}/new`, '_blank')
}
</script>
