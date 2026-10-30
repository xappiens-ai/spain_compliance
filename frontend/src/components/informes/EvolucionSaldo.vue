<template>
  <div class="h-[280px] w-full">
    <EChart :option="opcion" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChart from '@/components/informes/EChart.vue'
import { COLOR } from '@/composables/paleta'
import {
  FUENTE,
  ejeValor,
  leyendaBase,
  lineaTooltip,
  tooltipBase,
} from '@/composables/graficos'
import { formatDate } from '@/composables/informe'

const props = defineProps({
  serie: { type: Array, required: true },
  saldoInicial: { type: Number, default: 0 },
  desde: { type: String, required: true },
  currency: { type: String, default: 'EUR' },
})

const opcion = computed(() => {
  const meses = new Map()
  for (const dia of props.serie) {
    const clave = `${dia.fecha.slice(0, 7)}-15`
    const mes = meses.get(clave) || { debe: 0, haber: 0 }
    mes.debe += dia.debe
    mes.haber += dia.haber
    meses.set(clave, mes)
  }
  const saldos = [
    [props.desde, props.saldoInicial],
    ...props.serie.map((d) => [d.fecha, d.saldo]),
  ]
  return {
    textStyle: { fontFamily: FUENTE },
    grid: { left: 8, right: 8, top: 40, bottom: 4, containLabel: true },
    legend: leyendaBase({ top: 0, left: 0 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (items) =>
        `<div style="font-weight:600;margin-bottom:6px">${formatDate(items[0].value[0])}</div>` +
        items
          .map((it) =>
            lineaTooltip(it.color, it.seriesName, it.value[1], props.currency),
          )
          .join(''),
    }),
    xAxis: {
      type: 'time',
      axisLabel: { color: COLOR.textoSuave, fontSize: 11 },
      axisLine: { lineStyle: { color: COLOR.rejilla } },
      splitLine: { show: false },
    },
    yAxis: [
      ejeValor(props.currency),
      ejeValor(props.currency, { splitLine: { show: false } }),
    ],
    series: [
      {
        name: __('Debe del mes'),
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 14,
        itemStyle: {
          color: 'rgba(16,185,129,0.55)',
          borderRadius: [3, 3, 0, 0],
        },
        data: [...meses].map(([fecha, m]) => [
          fecha,
          Math.round(m.debe * 100) / 100,
        ]),
      },
      {
        name: __('Haber del mes'),
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 14,
        itemStyle: { color: 'rgba(244,63,94,0.5)', borderRadius: [3, 3, 0, 0] },
        data: [...meses].map(([fecha, m]) => [
          fecha,
          Math.round(m.haber * 100) / 100,
        ]),
      },
      {
        name: __('Saldo'),
        type: 'line',
        step: 'end',
        symbol: 'none',
        lineStyle: { width: 2.5, color: COLOR.total },
        itemStyle: { color: COLOR.total },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79,70,229,0.22)' },
              { offset: 1, color: 'rgba(79,70,229,0.02)' },
            ],
          },
        },
        data: saldos,
      },
    ],
  }
})
</script>
