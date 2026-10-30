<template>
  <div class="flex flex-col gap-5">
    <div
      class="flex items-center justify-between gap-3 rounded-xl px-4 py-3"
      :class="fondoManiobra >= 0 ? 'bg-surface-green-1' : 'bg-surface-red-1'"
    >
      <div>
        <div class="text-sm font-medium text-ink-gray-7">
          {{ __('Fondo de maniobra') }}
        </div>
        <div class="text-xs text-ink-gray-5">
          {{ __('Activo corriente menos pasivo corriente') }}
        </div>
      </div>
      <div class="text-right">
        <div
          class="text-3xl font-semibold tabular-nums"
          :class="fondoManiobra >= 0 ? 'text-ink-green-8' : 'text-ink-red-8'"
        >
          {{ formatCompact(fondoManiobra, currency) }}
        </div>
        <div class="text-xs text-ink-gray-6">
          {{
            fondoManiobra >= 0
              ? __('El circulante cubre las deudas a corto')
              : __('Las deudas a corto superan al circulante')
          }}
        </div>
      </div>
    </div>

    <ul class="flex flex-col gap-4">
      <li v-for="fila in filas" :key="fila.key">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="text-base font-medium text-ink-gray-8">
              {{ fila.label }}
            </div>
            <div class="truncate text-xs text-ink-gray-5">
              {{ fila.formula }}
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <span class="text-xl font-semibold tabular-nums text-ink-gray-9">{{
              fila.texto
            }}</span>
            <Badge
              v-if="fila.estado"
              :label="__(fila.estado.label)"
              :theme="fila.estado.tema"
              variant="subtle"
            />
          </div>
        </div>
        <div class="relative mt-2.5 h-2">
          <div class="flex h-full overflow-hidden rounded-full">
            <div
              v-for="(banda, i) in fila.bandas"
              :key="i"
              class="h-full"
              :style="{
                width: `${banda.ancho}%`,
                background: `${banda.color}40`,
              }"
            />
          </div>
          <div
            v-if="fila.posAnterior !== null"
            class="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-outline-gray-4 bg-surface-base"
            :style="{ left: `${fila.posAnterior}%` }"
            :title="__('{0}: {1}', periodos[1], fila.textoAnterior)"
          />
          <div
            v-if="fila.pos !== null"
            class="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-outline-base ring-1 ring-outline-gray-3 transition-all duration-700"
            :style="{
              left: `${fila.pos}%`,
              background: fila.estado?.color || '#64748B',
            }"
          />
        </div>
        <div
          class="mt-1 flex justify-between text-2xs tabular-nums text-ink-gray-4"
        >
          <span>{{ fila.min }}</span>
          <span v-if="fila.posAnterior !== null" class="text-ink-gray-5"
            >○ {{ periodos[1] }}: {{ fila.textoAnterior }}</span
          >
          <span>{{ fila.max }}</span>
        </div>
      </li>
    </ul>
    <p class="text-xs text-ink-gray-5">
      {{
        __(
          'Rangos orientativos de análisis de balances. Dependen del sector y del modelo de negocio.',
        )
      }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import { ESTADO_RATIO } from '@/composables/paleta'
import { formatCompact, formatPct, formatRatio } from '@/composables/informe'

const props = defineProps({
  ratios: { type: Array, required: true },
  periodos: { type: Array, required: true },
  currency: { type: String, default: 'EUR' },
})

const DEFINICIONES = [
  {
    key: 'liquidez',
    label: __('Liquidez general'),
    formula: __('Activo corriente / pasivo corriente'),
    escala: [0, 3],
    bandas: [
      [1, 'riesgo'],
      [1.5, 'ajustado'],
      [2, 'optimo'],
      [3, 'holgado'],
    ],
  },
  {
    key: 'acida',
    label: __('Prueba ácida'),
    formula: __('(Activo corriente − existencias) / pasivo corriente'),
    escala: [0, 2],
    bandas: [
      [0.7, 'riesgo'],
      [1, 'ajustado'],
      [1.5, 'optimo'],
      [2, 'holgado'],
    ],
  },
  {
    key: 'disponibilidad',
    label: __('Disponibilidad'),
    formula: __('Efectivo / pasivo corriente'),
    escala: [0, 1],
    bandas: [
      [0.1, 'riesgo'],
      [0.3, 'optimo'],
      [1, 'holgado'],
    ],
  },
  {
    key: 'endeudamiento',
    label: __('Endeudamiento'),
    formula: __('Pasivo / (patrimonio neto + pasivo)'),
    escala: [0, 1],
    porcentaje: true,
    bandas: [
      [0.4, 'holgado'],
      [0.6, 'optimo'],
      [0.8, 'ajustado'],
      [1, 'riesgo'],
    ],
  },
  {
    key: 'solvencia',
    label: __('Solvencia'),
    formula: __('Activo total / pasivo'),
    escala: [0, 3],
    bandas: [
      [1, 'riesgo'],
      [1.5, 'ajustado'],
      [3, 'optimo'],
    ],
  },
  {
    key: 'calidad_deuda',
    label: __('Calidad de la deuda'),
    formula: __('Pasivo corriente / pasivo'),
    escala: [0, 1],
    porcentaje: true,
    bandas: [
      [0.5, 'optimo'],
      [0.8, 'ajustado'],
      [1, 'riesgo'],
    ],
  },
]

const fondoManiobra = computed(() => props.ratios[0]?.fondo_maniobra || 0)

function posicion(valor, [min, max]) {
  if (valor === null || valor === undefined) return null
  return Math.min(Math.max((valor - min) / (max - min), 0), 1) * 100
}

function estado(valor, definicion) {
  if (valor === null || valor === undefined) return null
  const banda =
    definicion.bandas.find(([hasta]) => valor <= hasta) ||
    definicion.bandas.at(-1)
  return ESTADO_RATIO[banda[1]]
}

function texto(valor, definicion) {
  return definicion.porcentaje ? formatPct(valor) : formatRatio(valor)
}

const filas = computed(() =>
  DEFINICIONES.map((d) => {
    const valor = props.ratios[0]?.[d.key] ?? null
    const anterior = props.ratios[1]?.[d.key] ?? null
    const [min, max] = d.escala
    let desde = min
    const bandas = d.bandas.map(([hasta, clave]) => {
      const ancho = ((Math.min(hasta, max) - desde) / (max - min)) * 100
      desde = hasta
      return { ancho, color: ESTADO_RATIO[clave].color }
    })
    return {
      ...d,
      bandas,
      texto: texto(valor, d),
      textoAnterior: texto(anterior, d),
      estado: estado(valor, d),
      pos: posicion(valor, d.escala),
      posAnterior:
        props.ratios.length > 1 ? posicion(anterior, d.escala) : null,
      min: d.porcentaje ? formatPct(min, 0) : formatRatio(min, 1),
      max: `${d.porcentaje ? formatPct(max, 0) : formatRatio(max, 1)}${d.porcentaje ? '' : '+'}`,
    }
  }),
)
</script>
