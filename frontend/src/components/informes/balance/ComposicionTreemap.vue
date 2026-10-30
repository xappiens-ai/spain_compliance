<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <div v-for="mapa in mapas" :key="mapa.key" class="flex flex-col gap-2">
      <div
        class="text-xs font-semibold uppercase tracking-widest text-ink-gray-5"
      >
        {{ mapa.titulo }}
      </div>
      <div v-if="mapa.datos.length" class="h-[340px] w-full">
        <EChart :option="opcion(mapa)" />
      </div>
      <div
        v-else
        class="flex h-[340px] items-center justify-center rounded-xl bg-surface-gray-1 text-base text-ink-gray-5"
      >
        {{ __('Sin saldos') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChart from '@/components/informes/EChart.vue'
import { COLOR } from '@/composables/paleta'
import { FUENTE, tooltipBase } from '@/composables/graficos'
import { formatCompact, formatMoney, formatPct } from '@/composables/informe'

const props = defineProps({
  activo: { type: Object, required: true },
  pasivo: { type: Object, required: true },
  indice: { type: Number, default: 0 },
  currency: { type: String, default: 'EUR' },
})

const COLOR_MASA = {
  A: COLOR.anc,
  B: COLOR.realizable,
  PN: COLOR.pn,
  PNC: COLOR.pnc,
  PC: COLOR.pc,
}

function limpiar(label) {
  return label.replace(/^([A-C]\)|A-\d\)|[IVX]+\.|\d+\.|[a-z]\))\s*/, '')
}

function convertir(nodo) {
  const i = props.indice
  const hijos = nodo.hijos?.length
    ? nodo.hijos.map(convertir)
    : (nodo.cuentas || []).map((grupo) => ({
        name: grupo.codigo ? `${grupo.codigo} ${grupo.nombre}` : grupo.nombre,
        value: grupo.importes[i],
      }))
  const positivos = hijos.filter((hijo) => hijo.value > 0.005)
  return {
    name: limpiar(nodo.label),
    value: nodo.importes[i],
    ...(positivos.length ? { children: positivos } : {}),
  }
}

const mapas = computed(() =>
  [
    { key: 'activo', titulo: __('Activo'), raiz: props.activo },
    {
      key: 'pasivo',
      titulo: __('Patrimonio neto y pasivo'),
      raiz: props.pasivo,
    },
  ].map((mapa) => ({
    ...mapa,
    total: mapa.raiz.importes[props.indice] || 0,
    datos: mapa.raiz.hijos
      .map((masa) => ({
        ...convertir(masa),
        itemStyle: { color: COLOR_MASA[masa.code] },
      }))
      .filter((masa) => masa.value > 0.005),
  })),
)

function opcion(mapa) {
  return {
    textStyle: { fontFamily: FUENTE },
    tooltip: tooltipBase({
      formatter: (params) => {
        const ruta = params.treePathInfo
          .slice(1)
          .map((p) => p.name)
          .join(' › ')
        return `<div style="font-weight:600;margin-bottom:4px">${ruta}</div>
          <b>${formatMoney(params.value, props.currency)}</b>
          <span style="color:#64748B"> · ${formatPct(mapa.total ? params.value / mapa.total : null)}</span>`
      },
    }),
    series: [
      {
        type: 'treemap',
        roam: false,
        nodeClick: 'zoomToNode',
        top: 0,
        left: 0,
        right: 0,
        bottom: 30,
        leafDepth: 2,
        squareRatio: 0.9,
        breadcrumb: {
          show: true,
          bottom: 0,
          height: 22,
          itemStyle: {
            color: '#F1F5F9',
            borderColor: '#E2E8F0',
            textStyle: { color: '#334155' },
          },
        },
        upperLabel: {
          show: true,
          height: 22,
          color: '#FFFFFF',
          fontWeight: 600,
          fontSize: 12,
        },
        label: {
          show: true,
          fontSize: 12,
          lineHeight: 15,
          overflow: 'truncate',
          formatter: (params) =>
            `{n|${params.name}}\n{v|${formatCompact(params.value, props.currency)}}`,
          rich: {
            n: {
              color: '#FFFFFF',
              fontSize: 12,
              fontWeight: 500,
              lineHeight: 15,
            },
            v: {
              color: 'rgba(255,255,255,0.85)',
              fontSize: 11,
              lineHeight: 14,
            },
          },
        },
        levels: [
          {
            itemStyle: { borderWidth: 0, gapWidth: 4 },
            upperLabel: { show: false },
          },
          {
            itemStyle: { borderColor: '#FFFFFF', borderWidth: 3, gapWidth: 3 },
          },
          {
            itemStyle: { borderColor: '#FFFFFF', borderWidth: 1, gapWidth: 1 },
            colorAlpha: [0.6, 0.95],
          },
          {
            itemStyle: { borderColor: '#FFFFFF', borderWidth: 1, gapWidth: 1 },
            colorAlpha: [0.5, 0.85],
          },
        ],
        name: mapa.titulo,
        data: mapa.datos,
      },
    ],
  }
}
</script>
