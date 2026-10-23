<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __(title), route: $route.fullPath }]" />
    </template>
    <template #right-header>
      <Button
        :label="__('Actualizar')"
        variant="subtle"
        :loading="loading"
        @click="$emit('refresh')"
      >
        <template #prefix>
          <LucideRefreshCcw class="size-4" />
        </template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex h-full flex-col gap-4 overflow-hidden p-4 sm:p-5">
    <div class="flex flex-wrap items-end gap-3">
      <FormControl
        v-model="company"
        type="select"
        :label="__('Compañía')"
        :options="companyOptions"
        class="min-w-56"
      />
      <FormControl
        v-if="!hideDates && !asOf"
        v-model="fromDate"
        type="date"
        :label="__('Desde')"
      />
      <FormControl
        v-if="!hideDates"
        v-model="toDate"
        type="date"
        :label="asOf ? __('A fecha') : __('Hasta')"
      />
      <slot name="filters" />
    </div>
    <p v-if="error" class="text-p-sm text-ink-red-3">{{ error }}</p>
    <div
      v-if="loading && !hasData"
      class="flex flex-1 items-center justify-center"
    >
      <LoadingIndicator :scale="8" />
    </div>
    <div v-else class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Breadcrumbs, Button, FormControl, LoadingIndicator } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import LucideRefreshCcw from '~icons/lucide/refresh-ccw'

const company = defineModel('company', { type: String, default: '' })
const fromDate = defineModel('fromDate', { type: String, default: '' })
const toDate = defineModel('toDate', { type: String, default: '' })

const props = defineProps({
  title: { type: String, required: true },
  companies: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hasData: { type: Boolean, default: false },
  asOf: { type: Boolean, default: false },
  hideDates: { type: Boolean, default: false },
})

defineEmits(['refresh'])

const companyOptions = computed(() =>
  props.companies.map((row) => ({ label: row.name, value: row.name })),
)
</script>
