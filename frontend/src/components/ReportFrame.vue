<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs
        :items="[
          { label: seccion || __('Informes') },
          { label: title, route: $route.fullPath },
        ]"
      />
    </template>
    <template #right-header>
      <slot name="acciones" />
      <Button
        v-if="exportable"
        :label="__('Exportar')"
        variant="ghost"
        :disabled="!hasData"
        @click="$emit('export')"
      >
        <template #prefix><LucideDownload class="size-4" /></template>
      </Button>
      <Button
        :label="__('Imprimir')"
        variant="ghost"
        :disabled="!hasData"
        @click="imprimir"
      >
        <template #prefix><LucidePrinter class="size-4" /></template>
      </Button>
      <Button
        :label="__('Actualizar')"
        variant="subtle"
        :loading="loading"
        @click="$emit('refresh')"
      >
        <template #prefix><LucideRefreshCcw class="size-4" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div
    class="relative flex min-h-0 flex-1 flex-col overflow-auto bg-surface-gray-1 print:overflow-visible print:bg-white"
  >
    <div
      v-if="loading && hasData"
      class="pointer-events-none sticky top-0 z-20 h-0.5 w-full overflow-hidden bg-surface-blue-2 print:hidden"
    >
      <div
        class="h-full w-1/3 animate-[cargando_1.1s_ease-in-out_infinite] bg-surface-blue-7"
      />
    </div>
    <div
      class="mx-auto flex w-full max-w-[1480px] flex-col gap-5 px-4 py-5 sm:px-6 print:max-w-none print:gap-3 print:p-0"
    >
      <header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div class="min-w-0">
          <h1
            class="text-6xl font-semibold leading-tight tracking-tight text-ink-gray-9 print:text-5xl"
          >
            {{ title }}
          </h1>
          <p class="mt-1 text-md text-ink-gray-6">
            <span v-if="company" class="font-medium text-ink-gray-8">{{
              company
            }}</span>
            <span v-if="companyInfo?.tax_id">
              · {{ __('NIF') }} {{ companyInfo.tax_id }}</span
            >
            <span v-if="subtitle"> · {{ subtitle }}</span>
          </p>
        </div>
        <div v-if="badges.length" class="flex flex-wrap items-center gap-2">
          <Badge
            v-for="badge in badges"
            :key="badge.label"
            :label="badge.label"
            :theme="badge.theme || 'gray'"
            variant="subtle"
            size="lg"
          />
        </div>
      </header>

      <div
        class="flex flex-wrap items-end gap-x-4 gap-y-3 rounded-xl border border-outline-gray-1 bg-surface-elevation-1 px-4 py-3 print:hidden"
      >
        <CampoFiltro v-if="companies.length > 1" :label="__('Compañía')">
          <Select v-model="company" :options="companyOptions" class="w-60" />
        </CampoFiltro>
        <PeriodPicker
          v-if="!hideDates"
          v-model:from="fromDate"
          v-model:to="toDate"
          :fiscal-years="fiscalYears"
          :today="today"
          :as-of="asOf"
        />
        <slot name="filters" />
      </div>

      <Alert v-if="error" theme="red" :title="error" />

      <div v-if="loading && !hasData" class="flex flex-col gap-4">
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div
            v-for="i in 4"
            :key="i"
            class="h-32 animate-pulse rounded-xl bg-surface-gray-2"
          />
        </div>
        <div class="h-80 animate-pulse rounded-xl bg-surface-gray-2" />
        <div class="h-96 animate-pulse rounded-xl bg-surface-gray-2" />
      </div>
      <div
        v-else
        class="flex flex-col gap-5 transition-opacity print:gap-3"
        :class="loading ? 'opacity-60' : ''"
      >
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Alert, Badge, Breadcrumbs, Button, Select } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import PeriodPicker from '@/components/informes/PeriodPicker.vue'
import LucideRefreshCcw from '~icons/lucide/refresh-ccw'
import LucideDownload from '~icons/lucide/download'
import LucidePrinter from '~icons/lucide/printer'

const company = defineModel('company', { type: String, default: '' })
const fromDate = defineModel('fromDate', { type: String, default: '' })
const toDate = defineModel('toDate', { type: String, default: '' })

const props = defineProps({
  title: { type: String, required: true },
  seccion: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  companies: { type: Array, default: () => [] },
  fiscalYears: { type: Array, default: () => [] },
  today: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hasData: { type: Boolean, default: false },
  asOf: { type: Boolean, default: false },
  hideDates: { type: Boolean, default: false },
  exportable: { type: Boolean, default: false },
  badges: { type: Array, default: () => [] },
})

defineEmits(['refresh', 'export'])

const companyOptions = computed(() =>
  props.companies.map((row) => ({ label: row.name, value: row.name })),
)
const companyInfo = computed(() =>
  props.companies.find((row) => row.name === company.value),
)

function imprimir() {
  window.print()
}
</script>
