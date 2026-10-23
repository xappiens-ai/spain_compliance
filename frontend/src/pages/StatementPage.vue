<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="title"
    :companies="companies"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(report.data)"
    :as-of="asOf"
    @refresh="load"
  >
    <p v-if="report.data?.message" class="text-p-sm text-ink-gray-6">
      {{ report.data.message }}
    </p>
    <p v-if="report.data?.fiscal_year" class="text-p-sm text-ink-gray-5">
      {{ __('Ejercicio') }} {{ report.data.fiscal_year }}
    </p>

    <div
      v-if="report.data?.rows?.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-white"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="sticky top-0 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-left font-medium">{{ __('Cuenta') }}</th>
            <th
              v-for="column in report.data.columns"
              :key="column.key"
              class="px-3 py-2 text-right font-medium"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in report.data.rows"
            :key="index"
            class="border-t border-outline-gray-1"
            :class="row.emphasis ? 'bg-surface-gray-1' : ''"
          >
            <td
              class="px-3 py-2 text-ink-gray-9"
              :class="row.emphasis ? 'font-medium' : ''"
              :style="{ paddingLeft: `${12 + row.indent * 16}px` }"
            >
              {{ row.label }}
            </td>
            <td
              v-for="column in report.data.columns"
              :key="column.key"
              class="px-3 py-2 text-right tabular-nums text-ink-gray-8"
              :class="row.emphasis ? 'font-medium' : ''"
            >
              {{ formatMoney(row.amounts[column.key], report.data.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      v-else-if="report.data"
      class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
    >
      {{ __('Sin movimientos en el periodo') }}
    </div>
  </ReportFrame>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import { errorMessage, formatMoney, useInformePeriodo } from '@/composables/informe'

const props = defineProps({
  title: { type: String, required: true },
  method: { type: String, required: true },
  asOf: { type: Boolean, default: false },
})

const { company, fromDate, toDate, companies, contexto, whenReady } = useInformePeriodo()

const report = createResource({ url: props.method })

function load() {
  const params = { company: company.value, to_date: toDate.value }
  if (!props.asOf) params.from_date = fromDate.value
  report.update({ params })
  report.reload()
}

whenReady(load)
</script>
