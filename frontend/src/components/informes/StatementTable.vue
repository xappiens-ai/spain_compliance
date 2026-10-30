<template>
  <section
    class="flex min-w-0 flex-col overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:overflow-visible"
  >
    <header
      class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-3 sm:px-5"
    >
      <div class="min-w-0">
        <h3 class="text-xl font-semibold text-ink-gray-9">{{ titulo }}</h3>
        <p v-if="subtitulo" class="mt-0.5 text-sm text-ink-gray-5">
          {{ subtitulo }}
        </p>
      </div>
      <div class="flex items-center gap-1 print:hidden">
        <Button
          size="sm"
          variant="ghost"
          :label="__('Desplegar')"
          @click="desplegarTodo"
        >
          <template #prefix><LucideChevronsUpDown class="size-3.5" /></template>
        </Button>
        <Button
          size="sm"
          variant="ghost"
          :label="__('Plegar')"
          @click="plegarTodo"
        >
          <template #prefix><LucideChevronsDownUp class="size-3.5" /></template>
        </Button>
      </div>
    </header>
    <div class="overflow-x-auto print:overflow-visible">
      <table
        class="w-full border-collapse text-base"
        :class="mensual ? 'min-w-[980px]' : 'min-w-[640px]'"
      >
        <thead>
          <tr
            class="border-b border-outline-gray-1 bg-surface-gray-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
          >
            <th
              class="sticky left-0 z-10 bg-surface-gray-1 px-4 py-2.5 text-left"
            >
              {{ __('Concepto') }}
            </th>
            <th v-if="mensual" class="w-28 px-2 py-2.5 text-center">
              {{ __('Mensual') }}
            </th>
            <template v-for="(periodo, i) in periodos" :key="`h${i}`">
              <th class="whitespace-nowrap px-3 py-2.5 text-right">
                {{ periodo }}
              </th>
              <th
                v-if="bases"
                class="w-36 whitespace-nowrap px-3 py-2.5 text-right"
              >
                {{ etiquetaPct }}
              </th>
            </template>
            <template v-if="periodos.length > 1">
              <th class="whitespace-nowrap px-3 py-2.5 text-right">
                {{ __('Variación') }}
              </th>
              <th class="w-20 px-3 py-2.5 text-right">%</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="fila in visibles"
            :key="fila.key"
            class="group border-b border-outline-gray-1 last:border-b-0"
            :class="[
              estiloFila(fila).fila,
              fila.pulsable ? 'cursor-pointer' : '',
            ]"
            @click="pulsar(fila)"
          >
            <td
              class="sticky left-0 z-[1] max-w-[28rem] py-2 pr-3"
              :class="estiloFila(fila).celda"
              :style="{ paddingLeft: `${14 + fila.profundidad * 18}px` }"
            >
              <div class="flex min-w-0 items-center gap-1.5">
                <button
                  v-if="fila.expandible"
                  type="button"
                  class="flex size-5 shrink-0 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3 print:hidden"
                  :aria-label="
                    abiertos.has(fila.key) ? __('Plegar') : __('Desplegar')
                  "
                  @click.stop="alternar(fila.key)"
                >
                  <LucideChevronRight
                    class="size-3.5 transition-transform"
                    :class="abiertos.has(fila.key) ? 'rotate-90' : ''"
                  />
                </button>
                <span v-else class="inline-block w-5 shrink-0 print:hidden" />
                <span
                  v-if="fila.codigoCuenta"
                  class="shrink-0 tabular-nums"
                  :class="
                    fila.clase === 'subcuenta'
                      ? 'text-ink-gray-4'
                      : 'text-ink-gray-5'
                  "
                >
                  {{ fila.codigoCuenta }}
                </span>
                <span class="truncate" :title="fila.label">{{
                  fila.label
                }}</span>
                <LucideArrowUpRight
                  v-if="fila.pulsable"
                  class="size-3.5 shrink-0 text-ink-gray-4 opacity-0 transition group-hover:opacity-100 print:hidden"
                />
              </div>
            </td>
            <td v-if="mensual" class="px-2 py-1">
              <Sparkline
                v-if="fila.serie"
                :valores="fila.serie"
                :color="fila.importes[0] < 0 ? COLOR.negativo : COLOR.positivo"
                :alto="22"
                :relleno="false"
              />
            </td>
            <template v-for="(periodo, i) in periodos" :key="`c${i}`">
              <td
                class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                :class="[
                  estiloFila(fila).importe,
                  i > 0 ? 'text-ink-gray-5' : '',
                ]"
              >
                {{ importe(fila.importes[i]) }}
              </td>
              <td v-if="bases" class="px-3 py-2">
                <div
                  v-if="pct(fila, i) !== null"
                  class="flex items-center justify-end gap-2"
                >
                  <div
                    class="h-1.5 w-14 overflow-hidden rounded-full bg-surface-gray-2 print:hidden"
                  >
                    <div
                      class="h-full rounded-full"
                      :style="{
                        width: `${Math.min(Math.abs(pct(fila, i)), 1) * 100}%`,
                        background: colorBarra(fila, i),
                      }"
                    />
                  </div>
                  <span
                    class="w-16 whitespace-nowrap text-right text-sm tabular-nums text-ink-gray-5"
                  >
                    {{ formatPct(pct(fila, i)) }}
                  </span>
                </div>
              </td>
            </template>
            <template v-if="periodos.length > 1">
              <td
                class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                :class="colorVariacion(fila)"
              >
                {{ importeVariacion(fila) }}
              </td>
              <td
                class="whitespace-nowrap px-3 py-2 text-right text-sm tabular-nums"
                :class="colorVariacion(fila)"
              >
                {{ pctVariacion(fila) }}
              </td>
            </template>
          </tr>
          <tr v-if="!visibles.length">
            <td
              :colspan="columnas"
              class="px-4 py-10 text-center text-base text-ink-gray-5"
            >
              {{ __('Sin importes en el periodo') }}
            </td>
          </tr>
        </tbody>
        <tfoot v-if="total">
          <tr
            class="border-t-2 border-outline-gray-3 bg-surface-gray-2 font-semibold text-ink-gray-9"
          >
            <td
              class="sticky left-0 z-[1] bg-surface-gray-2 px-4 py-3 uppercase tracking-wide"
            >
              {{ total.label }}
            </td>
            <td v-if="mensual" />
            <template v-for="(periodo, i) in periodos" :key="`t${i}`">
              <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                {{ importe(total.importes[i]) }}
              </td>
              <td
                v-if="bases"
                class="px-3 py-3 text-right text-sm tabular-nums text-ink-gray-6"
              >
                {{ bases[i] ? formatPct(1) : '' }}
              </td>
            </template>
            <template v-if="periodos.length > 1">
              <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                {{ importeVariacion(total) }}
              </td>
              <td
                class="whitespace-nowrap px-3 py-3 text-right text-sm tabular-nums"
              >
                {{ pctVariacion(total) }}
              </td>
            </template>
          </tr>
        </tfoot>
      </table>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import Sparkline from '@/components/informes/Sparkline.vue'
import { COLOR } from '@/composables/paleta'
import { formatNumber, formatPct, variacion } from '@/composables/informe'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideChevronsUpDown from '~icons/lucide/chevrons-up-down'
import LucideChevronsDownUp from '~icons/lucide/chevrons-down-up'
import LucideArrowUpRight from '~icons/lucide/arrow-up-right'

const props = defineProps({
  titulo: { type: String, default: '' },
  subtitulo: { type: String, default: '' },
  nodos: { type: Array, required: true },
  total: { type: Object, default: null },
  periodos: { type: Array, required: true },
  bases: { type: Array, default: null },
  etiquetaPct: { type: String, default: '%' },
  detalle: { type: String, default: 'partidas' },
  mostrarCeros: { type: Boolean, default: false },
  mensual: { type: Object, default: null },
  tono: { type: String, default: 'balance' },
})

const emit = defineEmits(['cuenta', 'enlace'])

const SIEMPRE_VISIBLES = new Set(['masa', 'submasa', 'subtotal', 'total'])

const filas = computed(() => {
  const salida = []
  const recorrer = (nodos, profundidad, padre) => {
    for (const nodo of nodos) {
      const key = `n:${nodo.code}`
      const conHijos = nodo.hijos?.length > 0
      const conCuentas = nodo.cuentas?.length > 0
      salida.push({
        key,
        padre,
        clase: 'nodo',
        tipo: nodo.tipo,
        code: nodo.code,
        label: nodo.label,
        importes: nodo.importes,
        profundidad,
        expandible: conHijos || conCuentas,
        serie: props.mensual?.[nodo.code] || null,
      })
      if (conHijos) {
        recorrer(nodo.hijos, profundidad + 1, key)
      } else if (conCuentas) {
        for (const grupo of nodo.cuentas) {
          const clave = `${key}:g:${grupo.codigo || grupo.nombre}`
          salida.push({
            key: clave,
            padre: key,
            clase: 'grupo',
            tipo: 'cuenta',
            label: grupo.nombre,
            codigoCuenta: grupo.codigo,
            importes: grupo.importes,
            profundidad: profundidad + 1,
            expandible: grupo.subcuentas.length > 0,
            enlace: grupo.enlace,
            pulsable: Boolean(grupo.enlace),
          })
          for (const sub of grupo.subcuentas) {
            salida.push({
              key: `${clave}:s:${sub.account}`,
              padre: clave,
              clase: 'subcuenta',
              tipo: 'subcuenta',
              label: sub.nombre,
              codigoCuenta: sub.numero,
              importes: sub.importes,
              profundidad: profundidad + 2,
              expandible: false,
              account: sub.account,
              pulsable: true,
            })
          }
        }
      }
    }
  }
  recorrer(props.nodos, 0, null)
  return salida
})

const porClave = computed(
  () => new Map(filas.value.map((fila) => [fila.key, fila])),
)

function abiertosPorDetalle(detalle) {
  const abiertos = new Set()
  for (const fila of filas.value) {
    if (fila.clase !== 'nodo' || !fila.expandible) continue
    const tieneNodosHijos = filas.value.some(
      (f) => f.padre === fila.key && f.clase === 'nodo',
    )
    if (fila.tipo === 'masa' || fila.tipo === 'submasa') {
      if (tieneNodosHijos || detalle === 'cuentas') abiertos.add(fila.key)
    } else if (fila.tipo === 'epigrafe' || fila.tipo === 'linea') {
      if ((detalle === 'partidas' && tieneNodosHijos) || detalle === 'cuentas')
        abiertos.add(fila.key)
    } else if (fila.tipo === 'partida' && detalle === 'cuentas') {
      abiertos.add(fila.key)
    }
  }
  return abiertos
}

const abiertos = ref(new Set())

watch(
  () => [props.detalle, props.nodos],
  () => {
    abiertos.value = abiertosPorDetalle(props.detalle)
  },
  { immediate: true },
)

function esCero(fila) {
  return fila.importes.every((v) => Math.abs(Number(v) || 0) < 0.005)
}

const visibles = computed(() => {
  const visible = (fila) => {
    if (!props.mostrarCeros && esCero(fila) && !SIEMPRE_VISIBLES.has(fila.tipo))
      return false
    if (!fila.padre) return true
    if (!abiertos.value.has(fila.padre)) return false
    return visible(porClave.value.get(fila.padre))
  }
  return filas.value.filter(visible)
})

const columnas = computed(
  () =>
    1 +
    (props.mensual ? 1 : 0) +
    props.periodos.length * (props.bases ? 2 : 1) +
    (props.periodos.length > 1 ? 2 : 0),
)

function alternar(key) {
  const nuevos = new Set(abiertos.value)
  if (nuevos.has(key)) nuevos.delete(key)
  else nuevos.add(key)
  abiertos.value = nuevos
}

function desplegarTodo() {
  abiertos.value = new Set(
    filas.value
      .filter((f) => f.expandible && f.clase === 'nodo')
      .map((f) => f.key),
  )
}

function plegarTodo() {
  abiertos.value = abiertosPorDetalle('epigrafes')
}

function pulsar(fila) {
  if (fila.clase === 'subcuenta')
    emit('cuenta', {
      account: fila.account,
      numero: fila.codigoCuenta,
      nombre: fila.label,
    })
  else if (fila.enlace) emit('enlace', fila.enlace)
  else if (fila.expandible) alternar(fila.key)
}

function importe(valor) {
  const v = Number(valor) || 0
  if (Math.abs(v) < 0.005) return '—'
  return v < 0 ? `(${formatNumber(-v)})` : formatNumber(v)
}

function pct(fila, i) {
  const base = props.bases?.[i]
  if (!base || Math.abs(base) < 0.005) return null
  const v = Number(fila.importes[i]) || 0
  if (Math.abs(v) < 0.005) return null
  return v / Math.abs(base)
}

function colorBarra(fila, i) {
  if (props.tono === 'pyg')
    return (fila.importes[i] || 0) < 0 ? COLOR.negativo : COLOR.positivo
  return (fila.importes[i] || 0) < 0 ? COLOR.negativo : COLOR.total
}

function importeVariacion(fila) {
  const { abs } = variacion(fila.importes[0], fila.importes[1])
  if (Math.abs(abs) < 0.005) return '—'
  return `${abs > 0 ? '+' : '−'}${formatNumber(Math.abs(abs))}`
}

function pctVariacion(fila) {
  const { abs, pct: p } = variacion(fila.importes[0], fila.importes[1])
  if (Math.abs(abs) < 0.005 || p === null) return ''
  return `${p > 0 ? '+' : '−'}${formatNumber(Math.abs(p) * 100, 1)} %`
}

function colorVariacion(fila) {
  const { abs } = variacion(fila.importes[0], fila.importes[1])
  if (Math.abs(abs) < 0.005) return 'text-ink-gray-4'
  if (props.tono !== 'pyg') return 'text-ink-gray-6'
  return abs > 0 ? 'text-ink-green-7' : 'text-ink-red-7'
}

function estiloFila(fila) {
  if (fila.tipo === 'subtotal') {
    const negativo = (fila.importes[0] || 0) < 0
    return {
      fila: negativo ? 'bg-surface-red-1' : 'bg-surface-blue-1',
      celda: `${negativo ? 'bg-surface-red-1' : 'bg-surface-blue-1'} font-semibold uppercase tracking-wide text-ink-gray-9 border-l-4 ${negativo ? 'border-l-outline-red-4' : 'border-l-outline-blue-4'}`,
      importe: 'font-semibold text-ink-gray-9',
    }
  }
  if (fila.tipo === 'masa') {
    return {
      fila: 'bg-surface-gray-1',
      celda:
        'bg-surface-gray-1 font-semibold uppercase tracking-wide text-ink-gray-9',
      importe: 'font-semibold text-ink-gray-9',
    }
  }
  if (fila.tipo === 'submasa') {
    return {
      fila: 'hover:bg-surface-gray-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-gray-1 font-semibold text-ink-gray-9',
      importe: 'font-semibold text-ink-gray-9',
    }
  }
  if (fila.tipo === 'epigrafe' || fila.tipo === 'linea') {
    return {
      fila: 'hover:bg-surface-gray-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-gray-1 font-medium text-ink-gray-9',
      importe: 'font-medium text-ink-gray-9',
    }
  }
  if (fila.clase === 'grupo') {
    return {
      fila: 'hover:bg-surface-gray-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-gray-1 text-sm text-ink-gray-7',
      importe: 'text-sm text-ink-gray-7',
    }
  }
  if (fila.clase === 'subcuenta') {
    return {
      fila: 'hover:bg-surface-blue-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-blue-1 text-sm text-ink-gray-6',
      importe: 'text-sm text-ink-gray-6',
    }
  }
  return {
    fila: 'hover:bg-surface-gray-1',
    celda:
      'bg-surface-elevation-1 group-hover:bg-surface-gray-1 text-ink-gray-7',
    importe: 'text-ink-gray-8',
  }
}
</script>
