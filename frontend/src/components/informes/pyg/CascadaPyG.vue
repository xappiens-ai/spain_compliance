<template>
  <div v-if="pasos.length > 1" class="h-[360px] w-full">
    <EChart :option="opcion" />
  </div>
  <div
    v-else
    class="flex h-[360px] items-center justify-center text-base text-ink-gray-5"
  >
    {{ __('Sin movimientos de resultados en el periodo') }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChart from '@/components/informes/EChart.vue'
import { COLOR, NOMBRE_CORTO_PYG } from '@/composables/paleta'
import { FUENTE, ejeValor, tooltipBase } from '@/composables/graficos'
import { formatCompact, formatMoney } from '@/composables/informe'

const props = defineProps({
  lineas: { type: Array, required: true },
  indice: { type: Number, default: 0 },
  currency: { type: String, default: 'EUR' },
})

const pasos = computed(() => {
  const valor = Object.fromEntries(
    props.lineas.map((l) => [l.code, l.importes[props.indice] || 0]),
  )
  const salida = []
  let acumulado = 0
  const delta = (etiqueta, importe) => {
    if (Math.abs(importe) < 0.005) return
    salida.push({
      etiqueta,
      desde: acumulado,
      hasta: acumulado + importe,
      importe,
      total: false,
    })
    acumulado += importe
  }
  const total = (etiqueta, importe, final = false) => {
    salida.push({
      etiqueta,
      desde: 0,
      hasta: importe,
      importe,
      total: true,
      final,
    })
    acumulado = importe
  }
  for (const code of ['1', '2', '3', '4', '5', '6', '7', '8'])
    delta(NOMBRE_CORTO_PYG[code], valor[code])
  delta(
    __('Otros de explotación'),
    ['9', '10', '11', '12', '13'].reduce((s, c) => s + valor[c], 0),
  )
  total(NOMBRE_CORTO_PYG['A.1'], valor['A.1'])
  delta(NOMBRE_CORTO_PYG['14'], valor['14'])
  delta(NOMBRE_CORTO_PYG['15'], valor['15'])
  delta(
    __('Otros financieros'),
    ['16', '17', '18', '19'].reduce((s, c) => s + valor[c], 0),
  )
  if (Math.abs(valor['A.2']) >= 0.005)
    total(NOMBRE_CORTO_PYG['A.3'], valor['A.3'])
  delta(NOMBRE_CORTO_PYG['20'], valor['20'])
  delta(NOMBRE_CORTO_PYG['21'], valor['21'])
  total(NOMBRE_CORTO_PYG['A.5'], valor['A.5'], true)
  const penultimo = salida[salida.length - 2]
  if (penultimo?.total) salida.splice(salida.length - 2, 1)
  return salida
})

function colorPaso(paso) {
  if (paso.total) {
    if (paso.final) return paso.importe >= 0 ? '#059669' : '#E11D48'
    return COLOR.subtotal
  }
  return paso.importe >= 0 ? COLOR.positivo : COLOR.negativo
}

function partirEtiqueta(texto) {
  const palabras = texto.split(' ')
  const lineas = []
  let actual = ''
  for (const palabra of palabras) {
    if ((actual + ' ' + palabra).trim().length > 13 && actual) {
      lineas.push(actual)
      actual = palabra
    } else {
      actual = `${actual} ${palabra}`.trim()
    }
  }
  if (actual) lineas.push(actual)
  return lineas.join('\n')
}

const opcion = computed(() => {
  const pasosActuales = pasos.value
  const colores = pasosActuales.map(colorPaso)
  return {
    textStyle: { fontFamily: FUENTE },
    animationDuration: 700,
    grid: { left: 12, right: 12, top: 28, bottom: 8, containLabel: true },
    tooltip: tooltipBase({
      trigger: 'item',
      formatter: (params) => {
        const paso = pasosActuales[params.dataIndex]
        const signo = paso.total ? '' : paso.importe >= 0 ? '+' : ''
        return `<div style="font-weight:600;margin-bottom:4px">${paso.etiqueta}</div>
          <div style="display:flex;justify-content:space-between;gap:16px"><span>${paso.total ? __('Importe') : __('Aporta')}</span><b>${signo}${formatMoney(paso.importe, props.currency)}</b></div>
          ${paso.total ? '' : `<div style="display:flex;justify-content:space-between;gap:16px;color:#64748B"><span>${__('Acumulado')}</span><span>${formatMoney(paso.hasta, props.currency)}</span></div>`}`
      },
    }),
    xAxis: {
      type: 'category',
      data: pasosActuales.map((p) => partirEtiqueta(p.etiqueta)),
      axisLabel: {
        color: COLOR.textoSuave,
        fontSize: 11,
        interval: 0,
        lineHeight: 14,
      },
      axisLine: { lineStyle: { color: COLOR.rejilla } },
      axisTick: { show: false },
    },
    yAxis: ejeValor(props.currency),
    series: [
      {
        type: 'custom',
        data: pasosActuales.map((p, i) => [i, p.desde, p.hasta]),
        renderItem: (params, api) => {
          const i = api.value(0)
          const inicio = api.coord([i, api.value(1)])
          const fin = api.coord([i, api.value(2)])
          const ancho = api.size([1, 0])[0] * 0.58
          const arriba = Math.min(inicio[1], fin[1])
          const alto = Math.max(Math.abs(inicio[1] - fin[1]), 2)
          const paso = pasosActuales[i]
          const hijos = [
            {
              type: 'rect',
              shape: {
                x: inicio[0] - ancho / 2,
                y: arriba,
                width: ancho,
                height: alto,
                r: 4,
              },
              style: { fill: colores[i] },
            },
            {
              type: 'text',
              style: {
                text: formatCompact(paso.importe, props.currency),
                x: inicio[0],
                y: arriba - 6,
                align: 'center',
                verticalAlign: 'bottom',
                fill: paso.total ? COLOR.texto : colores[i],
                font: `600 11px ${FUENTE}`,
              },
            },
          ]
          if (i < pasosActuales.length - 1) {
            const siguiente = api.coord([i + 1, paso.hasta])
            hijos.push({
              type: 'line',
              shape: {
                x1: inicio[0] + ancho / 2,
                y1: fin[1],
                x2: siguiente[0] - ancho / 2,
                y2: fin[1],
              },
              style: { stroke: '#94A3B8', lineWidth: 1, lineDash: [3, 3] },
            })
          }
          return { type: 'group', children: hijos }
        },
      },
    ],
  }
})
</script>
