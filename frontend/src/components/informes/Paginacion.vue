<template>
  <div
    v-if="total"
    class="flex flex-wrap items-center justify-between gap-3 text-sm text-ink-gray-6 print:hidden"
  >
    <span class="tabular-nums">
      {{
        __('{0}–{1} de {2} {3}', desde, hasta, formatNumber(total, 0), etiqueta)
      }}
    </span>
    <div class="flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        :disabled="pagina <= 1"
        @click="pagina = 1"
      >
        <template #icon><LucideChevronsLeft class="size-4" /></template>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        :disabled="pagina <= 1"
        @click="pagina -= 1"
      >
        <template #icon><LucideChevronLeft class="size-4" /></template>
      </Button>
      <template v-for="item in botones" :key="item.key">
        <span v-if="item.hueco" class="px-1 text-ink-gray-4">…</span>
        <Button
          v-else
          size="sm"
          class="min-w-8 tabular-nums"
          :variant="item.numero === pagina ? 'solid' : 'ghost'"
          :label="String(item.numero)"
          @click="pagina = item.numero"
        />
      </template>
      <Button
        variant="ghost"
        size="sm"
        :disabled="pagina >= paginas"
        @click="pagina += 1"
      >
        <template #icon><LucideChevronRight class="size-4" /></template>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        :disabled="pagina >= paginas"
        @click="pagina = paginas"
      >
        <template #icon><LucideChevronsRight class="size-4" /></template>
      </Button>
      <Select
        v-if="tamanos.length"
        v-model="tamano"
        :options="opcionesTamano"
        class="ml-2 w-32"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button, Select } from 'frappe-ui'
import { formatNumber } from '@/composables/informe'
import LucideChevronLeft from '~icons/lucide/chevron-left'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideChevronsLeft from '~icons/lucide/chevrons-left'
import LucideChevronsRight from '~icons/lucide/chevrons-right'

const pagina = defineModel('page', { type: Number, default: 1 })
const tamano = defineModel('pageSize', { type: Number, default: 50 })

const props = defineProps({
  paginas: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  etiqueta: { type: String, default: '' },
  tamanos: { type: Array, default: () => [] },
})

const desde = computed(() =>
  formatNumber((pagina.value - 1) * tamano.value + 1, 0),
)
const hasta = computed(() =>
  formatNumber(Math.min(pagina.value * tamano.value, props.total), 0),
)

const opcionesTamano = computed(() =>
  props.tamanos.map((n) => ({ label: __('{0} por página', n), value: n })),
)

const botones = computed(() => {
  const total = props.paginas
  const actual = pagina.value
  const numeros = new Set([1, total, actual - 1, actual, actual + 1])
  const lista = [...numeros]
    .filter((n) => n >= 1 && n <= total)
    .sort((a, b) => a - b)
  const salida = []
  let anterior = 0
  for (const numero of lista) {
    if (numero - anterior > 1) salida.push({ key: `h${numero}`, hueco: true })
    salida.push({ key: numero, numero })
    anterior = numero
  }
  return salida
})
</script>
