<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Libro mayor')"
    :companies="companies"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error || cuentas.error)"
    :has-data="Boolean(report.data)"
    @refresh="load"
  >
    <template #filters>
      <FormControl
        v-model="account"
        type="select"
        :label="__('Cuenta')"
        :options="accountOptions"
        class="min-w-64"
      />
    </template>

    <p v-if="report.data?.truncated" class="text-p-sm text-ink-gray-6">
      {{
        __('Se muestran los primeros {0} de {1} movimientos. Acote la cuenta o el periodo.', report.data.rows.length, report.data.total)
      }}
    </p>
    <p
      v-if="report.data?.opening_balance != null"
      class="text-p-sm text-ink-gray-6"
    >
      {{ __('Saldo anterior') }}:
      {{ formatMoney(report.data.opening_balance, report.data.currency) }}
    </p>

    <div
      v-if="report.data?.rows?.length"
      class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-white"
    >
      <table class="min-w-full border-collapse text-base">
        <thead class="sticky top-0 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2 text-left font-medium">{{ __('Fecha') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Cuenta') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Documento') }}</th>
            <th class="px-3 py-2 text-left font-medium">{{ __('Tercero') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Debe') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Haber') }}</th>
            <th
              v-if="report.data.opening_balance != null"
              class="px-3 py-2 text-right font-medium"
            >
              {{ __('Saldo') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in report.data.rows"
            :key="row.name"
            class="cursor-pointer border-t border-outline-gray-1 hover:bg-surface-gray-1"
            @click="openDesk(row.voucher_type, row.voucher_no)"
          >
            <td class="px-3 py-2">{{ formatDate(row.posting_date) }}</td>
            <td class="max-w-xs truncate px-3 py-2">{{ row.account }}</td>
            <td class="px-3 py-2">
              <span class="text-ink-gray-5">{{ row.voucher_type }}</span>
              {{ row.voucher_no }}
            </td>
            <td class="max-w-xs truncate px-3 py-2">{{ row.party || row.against }}</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.debit, report.data.currency) }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ formatMoney(row.credit, report.data.currency) }}
            </td>
            <td
              v-if="report.data.opening_balance != null"
              class="px-3 py-2 text-right tabular-nums"
            >
              {{ formatMoney(row.balance, report.data.currency) }}
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
import { computed, ref, watch } from 'vue'
import { createResource, dayjs, FormControl } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import { errorMessage, formatMoney, openDesk, useInformePeriodo } from '@/composables/informe'

const account = ref('')
const { company, fromDate, toDate, companies, contexto, whenReady } = useInformePeriodo()

const cuentas = createResource({
  url: 'spain_compliance.api.informes.plan_cuentas',
})
const report = createResource({
  url: 'spain_compliance.api.informes.libro_mayor',
})

const accountOptions = computed(() => [
  { label: __('Todas las cuentas'), value: '' },
  ...(cuentas.data?.accounts || []).map((row) => ({
    label: row.account_number
      ? `${row.account_number} - ${row.account_name}`
      : row.account_name,
    value: row.name,
  })),
])

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
      account: account.value || undefined,
    },
  })
  report.reload()
}

watch(company, (value) => {
  account.value = ''
  if (!value) return
  cuentas.update({ params: { company: value } })
  cuentas.reload()
})

watch(account, () => {
  if (company.value && fromDate.value && toDate.value) load()
})

whenReady(load)

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}
</script>
