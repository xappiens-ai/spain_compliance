<template>
  <div v-if="base > 0" class="flex flex-1 flex-col gap-5">
    <p class="text-lg leading-snug text-ink-gray-7">
      <template v-if="resultado >= 0">
        {{ __('De cada 100 € que ingresa la empresa, se quedan') }}
        <span class="font-semibold text-ink-green-7"
          >{{ formatNumber(porCien(resultado), 1) }} €</span
        >
        {{ __('como beneficio.') }}
      </template>
      <template v-else>
        {{ __('Por cada 100 € de ingresos, los gastos suman') }}
        <span class="font-semibold text-ink-red-7"
          >{{ formatNumber(100 + porCien(-resultado), 1) }} €</span
        >:
        {{ __('se pierden') }}
        <span class="font-semibold text-ink-red-7"
          >{{ formatNumber(porCien(-resultado), 1) }} €</span
        >.
      </template>
    </p>

    <div class="relative">
      <div
        class="flex h-10 w-full overflow-hidden rounded-lg bg-surface-gray-2"
      >
        <div
          v-for="seg in segmentos"
          :key="seg.code"
          class="h-full transition-all duration-700 first:rounded-l-lg last:rounded-r-lg"
          :style="{
            width: `${(seg.valor / escala) * 100}%`,
            background: seg.color,
          }"
          :title="`${seg.nombre}: ${formatNumber(porCien(seg.valor), 1)} €`"
        />
      </div>
      <div
        v-if="resultado < 0"
        class="absolute -top-1 bottom-[-4px] w-0.5 bg-ink-gray-9"
        :style="{ left: `${(base / escala) * 100}%` }"
        :title="__('100 € de ingresos')"
      />
    </div>

    <ul class="flex flex-col gap-2">
      <li
        v-for="seg in segmentos"
        :key="seg.code"
        class="flex items-center gap-3 text-base"
      >
        <span
          class="size-2.5 shrink-0 rounded-sm"
          :style="{ background: seg.color }"
        />
        <span class="min-w-0 flex-1 truncate text-ink-gray-7">{{
          seg.nombre
        }}</span>
        <span class="tabular-nums font-semibold text-ink-gray-9"
          >{{ formatNumber(porCien(seg.valor), 1) }} €</span
        >
      </li>
    </ul>
    <p class="mt-auto text-xs text-ink-gray-5">
      {{
        __(
          'Base: {0} de ingresos de la cuenta de resultados.',
          formatMoney(base, currency),
        )
      }}
    </p>
  </div>
  <div
    v-else
    class="flex flex-1 items-center justify-center text-base text-ink-gray-5"
  >
    {{ __('Sin ingresos en el periodo') }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { COLOR_PYG, NOMBRE_CORTO_PYG } from '@/composables/paleta'
import { formatMoney, formatNumber } from '@/composables/informe'

const props = defineProps({
  lineas: { type: Array, required: true },
  indice: { type: Number, default: 0 },
  currency: { type: String, default: 'EUR' },
})

const partidas = computed(() => props.lineas.filter((l) => !l.subtotal))
const base = computed(() =>
  partidas.value.reduce(
    (s, l) => s + Math.max(l.importes[props.indice] || 0, 0),
    0,
  ),
)
const resultado = computed(
  () => props.lineas.find((l) => l.code === 'A.5')?.importes[props.indice] || 0,
)

const segmentos = computed(() => {
  const gastos = partidas.value
    .map((l) => ({ code: l.code, valor: -(l.importes[props.indice] || 0) }))
    .filter((g) => g.valor > 0.005)
    .sort((a, b) => b.valor - a.valor)
    .map((g) => ({
      ...g,
      nombre: NOMBRE_CORTO_PYG[g.code],
      color: COLOR_PYG[g.code],
    }))
  if (resultado.value > 0.005) {
    gastos.push({
      code: 'beneficio',
      valor: resultado.value,
      nombre: __('Beneficio'),
      color: '#059669',
    })
  }
  return gastos
})

const escala = computed(() =>
  Math.max(
    base.value,
    segmentos.value.reduce((s, g) => s + g.valor, 0),
  ),
)

function porCien(valor) {
  return base.value ? (valor / base.value) * 100 : 0
}
</script>
