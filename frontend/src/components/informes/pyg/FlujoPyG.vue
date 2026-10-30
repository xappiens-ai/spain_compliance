<template>
  <div v-if="enlaces.length" class="h-[380px] w-full">
    <EChart :option="opcion" />
  </div>
  <div
    v-else
    class="flex h-[380px] items-center justify-center text-base text-ink-gray-5"
  >
    {{ __('Sin ingresos ni gastos en el periodo') }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChart from '@/components/informes/EChart.vue'
import { COLOR_PYG, NOMBRE_CORTO_PYG } from '@/composables/paleta'
import { FUENTE, tooltipBase } from '@/composables/graficos'
import { formatCompact, formatMoney } from '@/composables/informe'

const props = defineProps({
  lineas: { type: Array, required: true },
  indice: { type: Number, default: 0 },
  currency: { type: String, default: 'EUR' },
})

const CENTRO = () => __('Ingresos totales')

const modelo = computed(() => {
  const partidas = props.lineas.filter((l) => !l.subtotal)
  const resultado =
    props.lineas.find((l) => l.code === 'A.5')?.importes[props.indice] || 0
  const ingresos = []
  const gastos = []
  for (const linea of partidas) {
    const valor = linea.importes[props.indice] || 0
    if (Math.abs(valor) < 0.005) continue
    const item = {
      code: linea.code,
      nombre: NOMBRE_CORTO_PYG[linea.code],
      valor: Math.abs(valor),
    }
    if (valor > 0) ingresos.push(item)
    else gastos.push(item)
  }
  ingresos.sort((a, b) => b.valor - a.valor)
  gastos.sort((a, b) => b.valor - a.valor)
  return { ingresos, gastos, resultado }
})

const nodos = computed(() => {
  const { ingresos, gastos, resultado } = modelo.value
  const lista = ingresos.map((i) => ({
    name: i.nombre,
    itemStyle: { color: COLOR_PYG[i.code] },
  }))
  if (resultado < -0.005)
    lista.push({
      name: __('Pérdida del periodo'),
      itemStyle: { color: '#E11D48' },
    })
  lista.push({ name: CENTRO(), itemStyle: { color: '#4F46E5' } })
  for (const g of gastos) {
    lista.push({ name: g.nombre, itemStyle: { color: COLOR_PYG[g.code] } })
  }
  if (resultado > 0.005)
    lista.push({ name: __('Beneficio'), itemStyle: { color: '#059669' } })
  return lista
})

const enlaces = computed(() => {
  const { ingresos, gastos, resultado } = modelo.value
  if (!ingresos.length && resultado >= -0.005) return []
  const centro = CENTRO()
  const lista = ingresos.map((i) => ({
    source: i.nombre,
    target: centro,
    value: i.valor,
  }))
  if (resultado < -0.005)
    lista.push({
      source: __('Pérdida del periodo'),
      target: centro,
      value: -resultado,
    })
  for (const g of gastos)
    lista.push({ source: centro, target: g.nombre, value: g.valor })
  if (resultado > 0.005)
    lista.push({ source: centro, target: __('Beneficio'), value: resultado })
  return lista
})

const opcion = computed(() => ({
  textStyle: { fontFamily: FUENTE },
  tooltip: tooltipBase({
    trigger: 'item',
    formatter: (params) =>
      params.dataType === 'edge'
        ? `${params.data.source} → ${params.data.target}<br/><b>${formatMoney(params.data.value, props.currency)}</b>`
        : `<b>${params.name}</b><br/>${formatMoney(params.value, props.currency)}`,
  }),
  series: [
    {
      type: 'sankey',
      left: 8,
      right: 150,
      top: 12,
      bottom: 12,
      nodeWidth: 14,
      nodeGap: 12,
      layoutIterations: 0,
      draggable: false,
      emphasis: { focus: 'adjacency' },
      data: nodos.value,
      links: enlaces.value,
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.32 },
      itemStyle: { borderWidth: 0, borderRadius: 3 },
      label: {
        color: '#0F172A',
        fontSize: 12,
        fontFamily: FUENTE,
        formatter: (params) =>
          `{n|${params.name}}\n{v|${formatCompact(params.value, props.currency)}}`,
        rich: {
          n: {
            fontSize: 12,
            color: '#334155',
            fontWeight: 500,
            lineHeight: 16,
          },
          v: { fontSize: 11, color: '#64748B', lineHeight: 14 },
        },
      },
    },
  ],
}))
</script>
