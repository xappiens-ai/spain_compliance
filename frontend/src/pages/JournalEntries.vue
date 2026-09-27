<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Asientos'), route: { name: 'JournalEntries' } }]" />
    </template>
    <template #right-header>
      <Button
        :label="__('Nuevo asiento')"
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
    <template #cell="{ column, item, row }">
      <Badge
        v-if="column.key === 'docstatus'"
        :label="docstatusLabel(item)"
        :theme="docstatusTheme(item)"
        variant="subtle"
      />
      <span
        v-else-if="column.key === 'total_debit'"
        class="truncate text-base tabular-nums"
      >
        {{ formatAmount(item, row) }}
      </span>
      <span v-else-if="column.key === 'posting_date'" class="truncate text-base">
        {{ formatDate(item) }}
      </span>
      <span v-else class="truncate text-base">{{ item }}</span>
    </template>
  </ListViewBuilder>
</template>

<script setup>
import { Badge, Breadcrumbs, Button, dayjs } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ListViewBuilder from '@/components/ListViewBuilder.vue'
import LucidePlus from '~icons/lucide/plus'
import LucideFileText from '~icons/lucide/file-text'

const listOptions = {
  doctype: 'Journal Entry',
  rowKey: 'name',
  fields: [
    'name',
    'title',
    'posting_date',
    'voucher_type',
    'company',
    'total_debit',
    'docstatus',
  ],
  orderBy: 'posting_date desc',
  pageLength: 20,
  columns: [
    { label: __('Asiento'), key: 'name', width: '11rem' },
    { label: __('Fecha'), key: 'posting_date', width: '9rem' },
    { label: __('Tipo'), key: 'voucher_type', width: '11rem' },
    { label: __('Compañía'), key: 'company' },
    { label: __('Debe'), key: 'total_debit', width: '10rem', align: 'end' },
    { label: __('Estado'), key: 'docstatus', width: '8rem' },
  ],
  onRowClick: (row) => openInDesk(row.name),
  emptyState: {
    title: __('Sin asientos contables'),
    description: __('Todavía no hay asientos registrados en ERPNext'),
  },
  emptyStateIcon: LucideFileText,
}

function docstatusLabel(value) {
  return { 0: __('Borrador'), 1: __('Validado'), 2: __('Cancelado') }[value] ?? value
}

function docstatusTheme(value) {
  return { 0: 'gray', 1: 'green', 2: 'red' }[value] ?? 'gray'
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
  const base = '/app/journal-entry'
  window.open(name ? `${base}/${name}` : `${base}/new`, '_blank')
}
</script>
