<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Terceros'), route: { name: 'Parties' } }]" />
    </template>
    <template #right-header>
      <div class="flex items-center gap-2">
        <TabButtons v-model="tab" :options="tabs" size="sm" />
        <Button :label="newLabel" theme="gray" variant="solid" @click="openNew">
          <template #prefix>
            <LucidePlus class="size-4" />
          </template>
        </Button>
      </div>
    </template>
  </LayoutHeader>

  <ListViewBuilder :key="tab" :options="listOptions">
    <template #cell="{ column, item }">
      <span v-if="isDateColumn(column.key)" class="truncate text-base">
        {{ item ? dayjs(item).format('DD/MM/YYYY') : '' }}
      </span>
      <span v-else class="truncate text-base">{{ item }}</span>
    </template>
  </ListViewBuilder>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Breadcrumbs, Button, TabButtons, dayjs } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ListViewBuilder from '@/components/ListViewBuilder.vue'
import LucidePlus from '~icons/lucide/plus'
import LucideContact from '~icons/lucide/contact'

const tab = ref('customers')
const tabs = [
  { label: __('Clientes'), value: 'customers' },
  { label: __('Proveedores'), value: 'suppliers' },
]

const configs = {
  customers: {
    doctype: 'Customer',
    deskPath: 'customer',
    newLabel: __('Nuevo cliente'),
    fields: ['name', 'customer_name', 'tax_id', 'customer_group', 'territory'],
    columns: [
      { label: __('ID'), key: 'name', width: '11rem' },
      { label: __('Nombre'), key: 'customer_name' },
      { label: __('NIF'), key: 'tax_id', width: '10rem' },
      { label: __('Grupo'), key: 'customer_group', width: '10rem' },
      { label: __('Territorio'), key: 'territory', width: '10rem' },
    ],
    emptyTitle: __('Sin clientes'),
    emptyDescription: __('Todavía no hay clientes en ERPNext'),
  },
  suppliers: {
    doctype: 'Supplier',
    deskPath: 'supplier',
    newLabel: __('Nuevo proveedor'),
    fields: ['name', 'supplier_name', 'tax_id', 'supplier_group', 'country'],
    columns: [
      { label: __('ID'), key: 'name', width: '11rem' },
      { label: __('Nombre'), key: 'supplier_name' },
      { label: __('NIF'), key: 'tax_id', width: '10rem' },
      { label: __('Grupo'), key: 'supplier_group', width: '10rem' },
      { label: __('País'), key: 'country', width: '9rem' },
    ],
    emptyTitle: __('Sin proveedores'),
    emptyDescription: __('Todavía no hay proveedores en ERPNext'),
  },
}

const current = computed(() => configs[tab.value])
const newLabel = computed(() => current.value.newLabel)

const listOptions = computed(() => ({
  doctype: current.value.doctype,
  rowKey: 'name',
  fields: current.value.fields,
  orderBy: 'modified desc',
  pageLength: 20,
  columns: current.value.columns,
  onRowClick: (row) => window.open(`/app/${current.value.deskPath}/${row.name}`, '_blank'),
  emptyState: {
    title: current.value.emptyTitle,
    description: current.value.emptyDescription,
  },
  emptyStateIcon: LucideContact,
}))

const dateKeys = new Set(['creation', 'modified'])
function isDateColumn(key) {
  return dateKeys.has(key)
}

function openNew() {
  window.open(`/app/${current.value.deskPath}/new`, '_blank')
}
</script>
