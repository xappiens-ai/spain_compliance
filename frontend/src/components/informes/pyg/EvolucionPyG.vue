<template>
  <div v-if="meses.length" class="h-[380px] w-full">
    <EChart :option="opcion" />
  </div>
  <div
    v-else
    class="flex h-[380px] items-center justify-center text-base text-ink-gray-5"
  >
    {{ __('Sin datos mensuales') }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChart from '@/components/informes/EChart.vue'
import { COLOR } from '@/composables/paleta'
import {
  FUENTE,
  ejeCategoria,
  ejeValor,
  leyendaBase,
  lineaTooltip,
  nombreMes,
  tooltipBase,
} from '@/composables/graficos'

const props = defineProps({
  meses: { type: Array, required: true },
  mensual: { type: Array, required: true },
  periodos: { type: Array, required: true },
  currency: { type: String, default: 'EUR' },
})

function acumular(valores) {
  let suma = 0
  return valores.map((v) => {
    suma += v || 0
    return Math.round(suma * 100) / 100
  })
}

const opcion = computed(() => {
  const actual = props.mensual[0] || {}
  const anterior = props.mensual[1] || null
  const ventas = actual['1'] || []
  const gastosExplotacion = (actual['A.1'] || []).map(
    (v, i) => (ventas[i] || 0) - v,
  )
  const series = [
    {
      name: __('Cifra de negocios'),
      type: 'bar',
      data: ventas,
      barMaxWidth: 22,
      itemStyle: { color: COLOR.positivo, borderRadius: [4, 4, 0, 0] },
    },
    {
      name: __('Gastos netos de explotación'),
      type: 'bar',
      data: gastosExplotacion,
      barMaxWidth: 22,
      itemStyle: { color: '#FDA4AF', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: __('Resultado acumulado'),
      type: 'line',
      yAxisIndex: 1,
      data: acumular(actual['A.5'] || []),
      smooth: 0.3,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 3, color: COLOR.total },
      itemStyle: { color: COLOR.total },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(79,70,229,0.18)' },
            { offset: 1, color: 'rgba(79,70,229,0)' },
          ],
        },
      },
    },
  ]
  if (anterior) {
    series.push({
      name: __('Acumulado {0}', props.periodos[1]),
      type: 'line',
      yAxisIndex: 1,
      data: acumular(anterior['A.5'] || []),
      smooth: 0.3,
      symbol: 'none',
      lineStyle: { width: 2, type: 'dashed', color: COLOR.neutro },
      itemStyle: { color: COLOR.neutro },
    })
  }
  return {
    textStyle: { fontFamily: FUENTE },
    grid: { left: 8, right: 8, top: 44, bottom: 4, containLabel: true },
    legend: leyendaBase({ top: 0, left: 0 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: 'rgba(148,163,184,0.12)' },
      },
      formatter: (items) =>
        `<div style="font-weight:600;margin-bottom:6px">${items[0].axisValueLabel}</div>` +
        items
          .map((it) =>
            lineaTooltip(it.color, it.seriesName, it.value, props.currency),
          )
          .join(''),
    }),
    xAxis: ejeCategoria(props.meses[0].map(nombreMes)),
    yAxis: [
      ejeValor(props.currency),
      ejeValor(props.currency, { splitLine: { show: false } }),
    ],
    series,
  }
})
</script>
