<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Libro de IVA')"
    :companies="companies"
    :fiscal-years="fiscalYears"
    :today="today"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(report.data)"
    @refresh="load"
  >
    <template #filters>
      <FormControl
        v-model="libro"
        type="select"
        :label="__('Libro')"
        :options="libroOptions"
        class="min-w-40"
      />
    </template>

    <div v-if="report.data" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="kpi in kpis"
        :key="kpi.label"
        class="rounded-lg border border-outline-gray-1 bg-surface-elevation-1 p-4"
      >
        <div class="text-p-sm text-ink-gray-6">{{ kpi.label }}</div>
        <div class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">
          {{ kpi.value }}
        </div>
      </div>
    </div>

    <p v-if="report.data?.sin_clasificar" class="text-p-sm text-ink-gray-6">
      {{
        __('{0} líneas pendientes de clasificar', report.data.sin_clasificar)
      }}
    </p>
    <p v-if="report.data?.truncated" class="text-p-sm text-ink-gray-6">
      {{
        __(
          'Se muestran las primeras {0} de {1} líneas.',
          report.data.rows.length,
          report.data.totals.filas,
        )
      }}
    </p>

    <div
      v-if="report.data?.por_clave?.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-elevation-1"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-left font-medium">{{ __('Clave') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Líneas') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Base') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Cuota') }}</th>
            <th class="px-3 py-2 text-right font-medium">
              {{ __('Deducible') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in report.data.por_clave"
            :key="row.clave"
            class="border-t border-outline-gray-1"
          >
            <td class="px-3 py-2">{{ row.clave }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ row.filas }}</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.base, report.data.currency) }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.cuota, report.data.currency) }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.deducible, report.data.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="report.data?.rows?.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-elevation-1"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="sticky top-0 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-left font-medium">{{ __('Fecha') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Número') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Tercero') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('NIF') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Clave') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Base') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Tipo') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Cuota') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in report.data.rows"
            :key="row.name"
            class="cursor-pointer border-t border-outline-gray-1 hover:bg-surface-gray-1"
            :class="row.sin_clasificar ? 'text-ink-amber-7' : ''"
            @click="openDesk(row.voucher_type, row.voucher_no)"
          >
            <td class="px-3 py-2">{{ formatDate(row.fecha) }}</td>
            <td class="px-3 py-2">{{ row.numero }}</td>
            <td class="max-w-xs truncate px-3 py-2">{{ row.party_name }}</td>
            <td class="px-3 py-2">{{ row.nif }}</td>
            <td class="px-3 py-2">{{ row.clave || '—' }}</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.base, report.data.currency) }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">{{ row.tipo }}%</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.cuota, report.data.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      v-else-if="report.data"
      class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
    >
      {{ __('Sin facturas en el libro para este periodo') }}
    </div>
  </ReportFrame>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { createResource, dayjs, FormControl } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import {
  errorMessage,
  formatMoney,
  openDesk,
  useInformePeriodo,
} from '@/composables/informe'

const libro = ref('Expedidas')
const libroOptions = [
  { label: __('Expedidas'), value: 'Expedidas' },
  { label: __('Recibidas'), value: 'Recibidas' },
]
const {
  company,
  fromDate,
  toDate,
  companies,
  fiscalYears,
  today,
  contexto,
  whenReady,
} = useInformePeriodo()

const report = createResource({
  url: 'spain_compliance.api.informes.libro_iva',
})

const kpis = computed(() => {
  const data = report.data
  if (!data) return []
  const currency = data.currency
  return [
    { label: __('Líneas'), value: String(data.totals.filas || 0) },
    {
      label: __('Base imponible'),
      value: formatMoney(data.totals.base, currency),
    },
    { label: __('Cuota'), value: formatMoney(data.totals.cuota, currency) },
    {
      label: __('Cuota deducible'),
      value: formatMoney(data.totals.deducible, currency),
    },
  ]
})

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
      libro: libro.value,
    },
  })
  report.reload()
}

watch(libro, () => {
  if (company.value && fromDate.value && toDate.value) load()
})

whenReady(load)

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}
</script>
