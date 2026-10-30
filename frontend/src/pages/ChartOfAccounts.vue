<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Plan de cuentas')"
    :seccion="__('Configuración')"
    :companies="companies"
    :loading="cuentas.loading || contexto.loading"
    :error="errorMessage(cuentas.error)"
    :has-data="Boolean(cuentas.data)"
    hide-dates
    @refresh="load"
  >
    <template #filters>
      <FormControl
        v-model="search"
        type="text"
        :label="__('Buscar')"
        :placeholder="__('Número o nombre')"
        class="min-w-48"
      />
    </template>

    <div
      v-if="filtered.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-elevation-1"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="sticky top-0 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-left font-medium">{{ __('Cuenta') }}</th>
            <th class="px-3 py-2 text-left font-medium">
              {{ __('Naturaleza') }}
            </th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Tipo') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filtered"
            :key="row.name"
            class="cursor-pointer border-t border-outline-gray-1 hover:bg-surface-gray-1"
            @click="openDesk('Account', row.name)"
          >
            <td
              class="px-3 py-2"
              :class="
                row.is_group ? 'font-medium text-ink-gray-9' : 'text-ink-gray-8'
              "
              :style="{ paddingLeft: `${12 + row.indent * 16}px` }"
            >
              <span v-if="row.account_number" class="tabular-nums">{{
                row.account_number
              }}</span>
              {{ row.account_name }}
            </td>
            <td class="px-3 py-2 text-ink-gray-6">{{ row.root_label }}</td>
            <td class="px-3 py-2 text-ink-gray-6">{{ row.account_type }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      v-else-if="cuentas.data"
      class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
    >
      {{ __('Ninguna cuenta coincide con la búsqueda') }}
    </div>
  </ReportFrame>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { createResource, FormControl } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import {
  errorMessage,
  openDesk,
  useInformePeriodo,
} from '@/composables/informe'

const search = ref('')
const { company, fromDate, toDate, companies, contexto } = useInformePeriodo()

const cuentas = createResource({
  url: 'spain_compliance.api.informes.plan_cuentas',
})

const filtered = computed(() => {
  const rows = cuentas.data?.accounts || []
  const term = search.value.trim().toLowerCase()
  if (!term) return rows
  return rows.filter((row) =>
    `${row.account_number} ${row.account_name}`.toLowerCase().includes(term),
  )
})

function load() {
  if (!company.value) return
  cuentas.update({ params: { company: company.value } })
  cuentas.reload()
}

watch(company, load)
</script>
