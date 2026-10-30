<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Ajustes')"
    :seccion="__('Configuración')"
    :companies="companies"
    :loading="datos.loading || contexto.loading"
    :error="errorMessage(datos.error)"
    :has-data="Boolean(datos.data)"
    hide-dates
    @refresh="load"
  >
    <div
      v-if="datos.data"
      class="max-w-3xl rounded-lg border border-outline-gray-1 bg-surface-elevation-1"
    >
      <div
        class="flex items-start justify-between gap-3 border-b border-outline-gray-1 p-4"
      >
        <div>
          <h2 class="text-2xl font-semibold text-ink-gray-9">
            {{ datos.data.company_name }}
          </h2>
          <p class="text-p-sm text-ink-gray-6">
            {{ datos.data.abbr }}
            <span v-if="datos.data.tax_id"> · {{ datos.data.tax_id }}</span>
            <span v-if="datos.data.country"> · {{ datos.data.country }}</span>
          </p>
        </div>
        <Button
          :label="__('Editar en Desk')"
          variant="subtle"
          @click="openDesk('Company', datos.data.company)"
        />
      </div>
      <dl class="divide-y divide-outline-gray-1">
        <div
          v-for="field in datos.data.fields"
          :key="field.fieldname"
          class="grid grid-cols-2 gap-3 px-4 py-3"
        >
          <dt class="text-p-sm text-ink-gray-6">{{ __(field.label) }}</dt>
          <dd class="text-base text-ink-gray-9">{{ display(field) }}</dd>
        </div>
      </dl>
    </div>
  </ReportFrame>
</template>

<script setup>
import { watch } from 'vue'
import { Button, createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import {
  errorMessage,
  openDesk,
  useInformePeriodo,
} from '@/composables/informe'

const { company, fromDate, toDate, companies, contexto } = useInformePeriodo()

const datos = createResource({
  url: 'spain_compliance.api.informes.ajustes',
})

function load() {
  if (!company.value) return
  datos.update({ params: { company: company.value } })
  datos.reload()
}

function display(field) {
  if (field.fieldtype === 'Check') return field.value ? __('Sí') : __('No')
  if (field.value === null || field.value === undefined || field.value === '')
    return '—'
  if (field.fieldtype === 'Percent') return `${field.value} %`
  return field.value
}

watch(company, load)
</script>
