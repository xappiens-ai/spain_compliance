<template>
  <div class="flex flex-col gap-4">
    <div v-if="periodos.length > 1" class="flex justify-end print:hidden">
      <TabButtons v-model="indice" :options="opcionesPeriodo" size="sm" />
    </div>

    <div
      class="grid grid-cols-[1fr_88px_1fr] text-center text-xs font-semibold uppercase tracking-widest text-ink-gray-5"
    >
      <span>{{ __('Activo') }}</span>
      <span />
      <span>{{ __('Patrimonio neto y pasivo') }}</span>
    </div>
    <div class="grid grid-cols-[1fr_88px_1fr]" :style="{ height: `${alto}px` }">
      <div
        class="flex flex-col justify-end overflow-hidden rounded-xl bg-surface-gray-1"
      >
        <BloqueMasa
          v-for="b in bloquesActivo"
          :key="b.key"
          :bloque="b"
          :visible="montado"
          :currency="currency"
        />
      </div>

      <div class="relative">
        <div
          class="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-surface-gray-3"
        />
        <div
          v-if="Math.abs(fondoManiobra) >= 0.005"
          class="absolute inset-x-2 flex items-center justify-center rounded-md border-2 border-dashed transition-all duration-700"
          :style="{
            bottom: `${montado ? Math.min(altoAC, altoPC) : 0}%`,
            height: `${montado ? Math.max(Math.abs(altoAC - altoPC), 0.6) : 0}%`,
            borderColor: fondoManiobra >= 0 ? '#10B981' : '#F43F5E',
            background:
              fondoManiobra >= 0
                ? 'rgba(16,185,129,0.10)'
                : 'rgba(244,63,94,0.10)',
          }"
          :title="
            __('Fondo de maniobra: {0}', formatMoney(fondoManiobra, currency))
          "
        />
        <div
          class="absolute left-1/2 z-10 flex -translate-x-1/2 translate-y-1/2 flex-col items-center whitespace-nowrap rounded-lg px-2 py-1 text-center ring-1 transition-all duration-700"
          :class="
            fondoManiobra >= 0
              ? 'bg-surface-green-1 text-ink-green-8 ring-outline-green-3'
              : 'bg-surface-red-1 text-ink-red-8 ring-outline-red-3'
          "
          :style="{ bottom: `${montado ? (altoAC + altoPC) / 2 : 0}%` }"
        >
          <span class="text-2xs font-semibold uppercase tracking-wide">{{
            __('F. maniobra')
          }}</span>
          <span class="text-sm font-semibold tabular-nums">{{
            formatCompact(fondoManiobra, currency)
          }}</span>
        </div>
      </div>

      <div
        class="flex flex-col justify-end overflow-hidden rounded-xl bg-surface-gray-1"
      >
        <BloqueMasa
          v-for="b in bloquesPasivo"
          :key="b.key"
          :bloque="b"
          :visible="montado"
          :currency="currency"
        />
      </div>
    </div>

    <p
      v-if="masa.pn < 0"
      class="rounded-lg bg-surface-red-1 px-3 py-2 text-sm text-ink-red-8"
    >
      {{
        __(
          'Patrimonio neto negativo ({0}): el pasivo supera al activo.',
          formatMoney(masa.pn, currency),
        )
      }}
    </p>

    <table class="w-full text-sm">
      <thead>
        <tr class="text-xs uppercase tracking-wide text-ink-gray-5">
          <th class="py-1.5 text-left font-medium">{{ __('Masa') }}</th>
          <th class="py-1.5 text-right font-medium">{{ periodos[indice] }}</th>
          <th class="py-1.5 text-right font-medium">%</th>
          <th v-if="periodos.length > 1" class="py-1.5 text-right font-medium">
            {{ __('Variación') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="fila in leyenda"
          :key="fila.key"
          class="border-t border-outline-gray-1"
        >
          <td class="py-1.5">
            <span class="flex items-center gap-2">
              <span
                class="size-2.5 rounded-sm"
                :style="{ background: fila.color }"
              />
              <span class="text-ink-gray-8">{{ fila.label }}</span>
            </span>
          </td>
          <td class="py-1.5 text-right tabular-nums text-ink-gray-9">
            {{ formatMoney(fila.valor, currency) }}
          </td>
          <td class="py-1.5 text-right tabular-nums text-ink-gray-5">
            {{ formatPct(total ? fila.valor / total : null) }}
          </td>
          <td
            v-if="periodos.length > 1"
            class="py-1.5 text-right tabular-nums text-ink-gray-7"
          >
            <span v-if="Math.abs(fila.delta) >= 0.005"
              >{{ fila.delta > 0 ? '+' : '−'
              }}{{ formatCompact(Math.abs(fila.delta), currency) }}</span
            >
            <span v-else class="text-ink-gray-4">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { TabButtons } from 'frappe-ui'
import { COLOR } from '@/composables/paleta'
import { formatCompact, formatMoney, formatPct } from '@/composables/informe'

const props = defineProps({
  masas: { type: Array, required: true },
  periodos: { type: Array, required: true },
  currency: { type: String, default: 'EUR' },
  alto: { type: Number, default: 440 },
})

const indice = ref(0)
const montado = ref(false)
onMounted(() => requestAnimationFrame(() => (montado.value = true)))

const opcionesPeriodo = computed(() =>
  props.periodos.map((label, i) => ({ label, value: i })),
)
const masa = computed(() => props.masas[indice.value] || props.masas[0])
const anterior = computed(
  () => (indice.value === 0 ? props.masas[1] : props.masas[0]) || null,
)

const DEFINICION_ACTIVO = [
  { key: 'anc', label: __('Activo no corriente'), color: COLOR.anc },
  { key: 'existencias', label: __('Existencias'), color: COLOR.existencias },
  { key: 'realizable', label: __('Realizable'), color: COLOR.realizable },
  { key: 'disponible', label: __('Disponible'), color: COLOR.disponible },
]
const DEFINICION_PASIVO = [
  { key: 'pn', label: __('Patrimonio neto'), color: COLOR.pn },
  { key: 'pnc', label: __('Pasivo no corriente'), color: COLOR.pnc },
  { key: 'pc', label: __('Pasivo corriente'), color: COLOR.pc },
]

const escala = computed(() => {
  const m = masa.value
  const izquierda = DEFINICION_ACTIVO.reduce(
    (s, d) => s + Math.max(m[d.key] || 0, 0),
    0,
  )
  const derecha = DEFINICION_PASIVO.reduce(
    (s, d) => s + Math.max(m[d.key] || 0, 0),
    0,
  )
  return Math.max(izquierda, derecha) || 1
})

const total = computed(() => masa.value.activo || 0)

function bloques(definicion) {
  return definicion.map((d) => {
    const valor = masa.value[d.key] || 0
    return {
      ...d,
      valor,
      pct: total.value ? valor / total.value : 0,
      alto: (Math.max(valor, 0) / escala.value) * 100,
    }
  })
}

const bloquesActivo = computed(() => bloques(DEFINICION_ACTIVO))
const bloquesPasivo = computed(() => bloques(DEFINICION_PASIVO))

const altoAC = computed(() =>
  bloquesActivo.value
    .filter((b) => b.key !== 'anc')
    .reduce((s, b) => s + b.alto, 0),
)
const altoPC = computed(
  () => bloquesPasivo.value.find((b) => b.key === 'pc').alto,
)
const fondoManiobra = computed(
  () => (masa.value.ac || 0) - (masa.value.pc || 0),
)

const leyenda = computed(() =>
  [...DEFINICION_ACTIVO, ...DEFINICION_PASIVO].map((d) => ({
    ...d,
    valor: masa.value[d.key] || 0,
    delta: anterior.value
      ? (masa.value[d.key] || 0) - (anterior.value[d.key] || 0)
      : 0,
  })),
)

const BloqueMasa = defineComponent({
  props: { bloque: Object, visible: Boolean, currency: String },
  setup(p) {
    return () => {
      const b = p.bloque
      const oscuro = b.color === COLOR.pnc
      const grande = b.alto >= 11
      const mediano = b.alto >= 4.5
      return h(
        'div',
        {
          class:
            'relative flex w-full shrink-0 flex-col items-center justify-center overflow-hidden border-t border-white/40 px-3 text-center transition-[height] duration-700 ease-out first:border-t-0',
          style: {
            height: `${p.visible ? b.alto : 0}%`,
            backgroundColor: b.color,
            backgroundImage:
              'linear-gradient(160deg, rgba(255,255,255,0.18), rgba(0,0,0,0.10))',
            color: oscuro ? '#451A03' : '#FFFFFF',
          },
          title: `${b.label}: ${formatMoney(b.valor, p.currency)} (${formatPct(b.pct)})`,
        },
        grande
          ? [
              h(
                'span',
                { class: 'text-sm font-semibold leading-tight' },
                b.label,
              ),
              h(
                'span',
                {
                  class:
                    'mt-0.5 text-xl font-semibold tabular-nums leading-tight',
                },
                formatCompact(b.valor, p.currency),
              ),
              h(
                'span',
                { class: 'text-xs tabular-nums opacity-80' },
                formatPct(b.pct),
              ),
            ]
          : mediano
            ? [
                h(
                  'span',
                  { class: 'truncate text-xs font-semibold' },
                  `${b.label} · ${formatPct(b.pct)}`,
                ),
              ]
            : [],
      )
    }
  },
})
</script>
