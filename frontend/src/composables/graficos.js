import { COLOR } from '@/composables/paleta'
import { formatCompact, formatMoney } from '@/composables/informe'

export const FUENTE =
  'InterVariable, Inter, ui-sans-serif, system-ui, sans-serif'

export function tooltipBase(extra = {}) {
  return {
    backgroundColor: '#FFFFFF',
    borderColor: COLOR.rejilla,
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: COLOR.texto, fontFamily: FUENTE, fontSize: 12 },
    extraCssText:
      'box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12); border-radius: 10px;',
    ...extra,
  }
}

export function ejeValor(currency, extra = {}) {
  return {
    type: 'value',
    axisLabel: {
      color: COLOR.textoSuave,
      fontFamily: FUENTE,
      fontSize: 11,
      formatter: (value) => formatCompact(value, currency),
    },
    splitLine: { lineStyle: { color: COLOR.rejilla, type: 'dashed' } },
    axisLine: { show: false },
    axisTick: { show: false },
    ...extra,
  }
}

export function ejeCategoria(data, extra = {}) {
  return {
    type: 'category',
    data,
    axisLabel: { color: COLOR.textoSuave, fontFamily: FUENTE, fontSize: 11 },
    axisLine: { lineStyle: { color: COLOR.rejilla } },
    axisTick: { show: false },
    ...extra,
  }
}

export function leyendaBase(extra = {}) {
  return {
    icon: 'roundRect',
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { color: COLOR.textoSuave, fontFamily: FUENTE, fontSize: 12 },
    ...extra,
  }
}

export function lineaTooltip(color, nombre, valor, currency) {
  return `<div style="display:flex;align-items:center;gap:8px;justify-content:space-between;min-width:200px">
    <span style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:2px;background:${color}"></span>${nombre}</span>
    <b style="font-variant-numeric:tabular-nums">${formatMoney(valor, currency)}</b></div>`
}

export function nombreMes(clave) {
  const [anio, mes] = String(clave).split('-').map(Number)
  const nombres = [
    'ene',
    'feb',
    'mar',
    'abr',
    'may',
    'jun',
    'jul',
    'ago',
    'sep',
    'oct',
    'nov',
    'dic',
  ]
  return `${nombres[(mes || 1) - 1]} ${String(anio).slice(2)}`
}
