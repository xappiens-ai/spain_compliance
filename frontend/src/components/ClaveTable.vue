<template>
  <section class="overflow-auto rounded-lg border border-outline-gray-1 bg-surface-white">
    <h3 class="px-3 py-2 text-base font-medium text-ink-gray-9">{{ title }}</h3>
    <table class="min-w-full border-collapse text-base">
      <thead class="bg-surface-gray-1 text-ink-gray-6">
        <tr>
          <th class="px-3 py-2 text-left font-medium">{{ __('Clave') }}</th>
          <th class="px-3 py-2 text-right font-medium">{{ __('Base') }}</th>
          <th class="px-3 py-2 text-right font-medium">{{ __('Cuota') }}</th>
          <th v-if="deductible" class="px-3 py-2 text-right font-medium">
            {{ __('Deducible') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.clave" class="border-t border-outline-gray-1">
          <td class="px-3 py-2">{{ row.clave }}</td>
          <td class="px-3 py-2 text-right tabular-nums">
            {{ formatMoney(row.base, currency) }}
          </td>
          <td class="px-3 py-2 text-right tabular-nums">
            {{ formatMoney(row.cuota, currency) }}
          </td>
          <td v-if="deductible" class="px-3 py-2 text-right tabular-nums">
            {{ formatMoney(row.deducible, currency) }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
import { formatMoney } from '@/composables/informe'

defineProps({
  title: { type: String, required: true },
  rows: { type: Array, default: () => [] },
  currency: { type: String, default: 'EUR' },
  deductible: { type: Boolean, default: false },
})
</script>
