<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Libro diario')"
    :companies="companies"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(report.data)"
    @refresh="load"
  >
    <p v-if="report.data" class="text-p-sm text-ink-gray-6">
      {{
        __(
          'Ejercicio {0}. La numeración es correlativa desde el {1} y solo incluye asientos validados.',
          report.data.fiscal_year,
          formatDate(report.data.fiscal_year_start),
        )
      }}
    </p>
    <p v-if="report.data?.truncated" class="text-p-sm text-ink-gray-6">
      {{
        __(
          'Se muestran los primeros {0} asientos del periodo. Acote las fechas para ver el resto.',
          report.data.totals.asientos_mostrados,
        )
      }}
    </p>

    <div
      v-if="report.data?.entries?.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-white"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="sticky top-0 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-right font-medium">{{ __('Nº') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Fecha') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Cuenta') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Descripción') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Concepto') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Documento') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Debe') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Haber') }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="entry in report.data.entries" :key="entry.voucher_type + entry.voucher_no">
            <tr
              v-for="(line, index) in entry.lines"
              :key="line.name"
              class="cursor-pointer border-t border-outline-gray-1 hover:bg-surface-gray-1"
              @click="openDesk(entry.voucher_type, entry.voucher_no)"
            >
              <td class="px-3 py-2 text-right tabular-nums">
                <span v-if="index === 0">{{ entry.numero }}</span>
              </td>
              <td class="whitespace-nowrap px-3 py-2">
                <span v-if="index === 0">{{ formatDate(entry.posting_date) }}</span>
              </td>
              <td class="whitespace-nowrap px-3 py-2 tabular-nums">
                {{ line.account_number || '—' }}
              </td>
              <td class="max-w-xs truncate px-3 py-2">{{ line.account_name }}</td>
              <td class="max-w-xs truncate px-3 py-2">
                <span v-if="index === 0" class="mr-2">
                  <Badge
                    :label="entry.clase"
                    :theme="claseTheme(entry.clase)"
                    variant="subtle"
                  />
                </span>
                {{ line.concepto }}
              </td>
              <td class="whitespace-nowrap px-3 py-2">
                <template v-if="index === 0">{{ entry.voucher_no }}</template>
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ line.debit ? formatMoney(line.debit, report.data.currency) : '' }}
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ line.credit ? formatMoney(line.credit, report.data.currency) : '' }}
              </td>
            </tr>
            <tr class="border-t border-outline-gray-1 bg-surface-gray-1 font-medium">
              <td colspan="6" class="px-3 py-2 text-right text-ink-gray-6">
                {{ __('Total asiento {0}', entry.numero) }}
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ formatMoney(entry.debit, report.data.currency) }}
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ formatMoney(entry.credit, report.data.currency) }}
              </td>
            </tr>
          </template>
          <tr class="border-t border-outline-gray-2 font-semibold">
            <td colspan="6" class="px-3 py-2 text-right">{{ __('Total del periodo') }}</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(report.data.totals.debe, report.data.currency) }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(report.data.totals.haber, report.data.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      v-else-if="report.data"
      class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
    >
      {{ __('Sin asientos validados en el periodo') }}
    </div>
    <p
      v-if="report.data?.entries?.length && !report.data.truncated && !report.data.cuadrado"
      class="text-p-sm text-ink-red-3"
    >
      {{ __('El debe y el haber del periodo no cuadran.') }}
    </p>
  </ReportFrame>
</template>

<script setup>
import { Badge, createResource, dayjs } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import { errorMessage, formatMoney, openDesk, useInformePeriodo } from '@/composables/informe'

const { company, fromDate, toDate, companies, contexto, whenReady } = useInformePeriodo()

const report = createResource({
  url: 'spain_compliance.api.informes.libro_diario',
})

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
    },
  })
  report.reload()
}

whenReady(load)

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}

function claseTheme(clase) {
  return { Apertura: 'blue', Regularización: 'orange', Diario: 'gray' }[clase] || 'gray'
}
</script>
