<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Liquidación de IVA')"
    :companies="companies"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(report.data)"
    @refresh="load"
  >
    <p class="text-p-sm text-ink-gray-5">
      {{
        __(
          'Borrador calculado desde el registro fiscal. No sustituye al modelo 303 presentado ante la AEAT.',
        )
      }}
    </p>

    <div v-if="report.data" class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-lg border border-outline-gray-1 bg-surface-white p-4">
        <div class="text-p-sm text-ink-gray-6">{{ __('IVA repercutido') }}</div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ formatMoney(report.data.repercutido.cuota, report.data.currency) }}
        </div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Base') }}
          {{ formatMoney(report.data.repercutido.base, report.data.currency) }}
          · {{ report.data.repercutido.filas }} {{ __('facturas') }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-1 bg-surface-white p-4">
        <div class="text-p-sm text-ink-gray-6">{{ __('IVA deducible') }}</div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ formatMoney(report.data.soportado.deducible, report.data.currency) }}
        </div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Cuota soportada') }}
          {{ formatMoney(report.data.soportado.cuota, report.data.currency) }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-1 bg-surface-white p-4">
        <div class="text-p-sm text-ink-gray-6">
          {{ resultadoLabel }}
        </div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ formatMoney(Math.abs(report.data.resultado), report.data.currency) }}
        </div>
      </div>
    </div>

    <ClaveTable
      v-if="report.data?.por_clave_expedidas?.length"
      :title="__('Expedidas por clave')"
      :rows="report.data.por_clave_expedidas"
      :currency="report.data.currency"
    />
    <ClaveTable
      v-if="report.data?.por_clave_recibidas?.length"
      :title="__('Recibidas por clave')"
      :rows="report.data.por_clave_recibidas"
      :currency="report.data.currency"
      deductible
    />
  </ReportFrame>
</template>

<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import ClaveTable from '@/components/ClaveTable.vue'
import { errorMessage, formatMoney, useInformePeriodo } from '@/composables/informe'

const { company, fromDate, toDate, companies, contexto, whenReady } = useInformePeriodo()

const report = createResource({
  url: 'spain_compliance.api.informes.liquidacion_iva',
})

const resultadoLabel = computed(() => {
  const valor = Number(report.data?.resultado) || 0
  if (valor > 0) return __('A ingresar')
  if (valor < 0) return __('A compensar')
  return __('Resultado')
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
</script>
