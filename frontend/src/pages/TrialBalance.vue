<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Sumas y saldos')"
    :subtitle="subtitulo"
    :companies="companies"
    :fiscal-years="fiscalYears"
    :today="today"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(datos)"
    :badges="insignias"
    exportable
    @refresh="load"
    @export="exportar"
  >
    <template #filters>
      <CampoFiltro :label="__('Nivel')">
        <TabButtons v-model="nivel" :options="opcionesNivel" />
      </CampoFiltro>
      <CampoFiltro :label="__('Buscar cuenta')">
        <TextInput
          v-model="busqueda"
          :placeholder="__('Número o nombre')"
          class="w-56"
          :debounce="200"
        >
          <template #prefix
            ><LucideSearch class="size-4 text-ink-gray-5"
          /></template>
        </TextInput>
      </CampoFiltro>
      <CampoFiltro :label="__('Solo con saldo final')">
        <Switch v-model="soloConSaldo" />
      </CampoFiltro>
    </template>

    <template v-if="datos">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard
          :label="__('Sumas debe')"
          :valor="formatCompact(t.debe, moneda)"
          :titulo="formatMoney(t.debe, moneda)"
          :color="COLOR.anc"
          :icono="iconos.debe"
          :pista="__('Movimientos del periodo')"
        />
        <KpiCard
          :label="__('Sumas haber')"
          :valor="formatCompact(t.haber, moneda)"
          :titulo="formatMoney(t.haber, moneda)"
          :color="COLOR.pn"
          :icono="iconos.haber"
          :pista="__('Movimientos del periodo')"
        />
        <KpiCard
          :label="__('Saldos deudores')"
          :valor="formatCompact(t.saldo_deudor, moneda)"
          :titulo="formatMoney(t.saldo_deudor, moneda)"
          :color="COLOR.realizable"
          :icono="iconos.deudor"
          :pista="__('Al cierre del periodo')"
        />
        <KpiCard
          :label="__('Saldos acreedores')"
          :valor="formatCompact(t.saldo_acreedor, moneda)"
          :titulo="formatMoney(t.saldo_acreedor, moneda)"
          :color="COLOR.pc"
          :icono="iconos.acreedor"
          :pista="__('Al cierre del periodo')"
        />
        <div
          class="flex flex-col justify-center gap-2 rounded-xl border p-4"
          :class="
            cuadra
              ? 'border-outline-green-2 bg-surface-green-1'
              : 'border-outline-red-2 bg-surface-red-1'
          "
        >
          <div
            class="flex items-center gap-2 text-lg font-semibold"
            :class="cuadra ? 'text-ink-green-8' : 'text-ink-red-8'"
          >
            <LucideCircleCheck v-if="cuadra" class="size-5" />
            <LucideCircleAlert v-else class="size-5" />
            {{ cuadra ? __('Cuadra') : __('No cuadra') }}
          </div>
          <div class="text-sm text-ink-gray-7">
            {{ datos.cuadre.sumas ? __('Debe = haber') : __('Debe ≠ haber') }} ·
            {{
              datos.cuadre.saldos
                ? __('Deudor = acreedor')
                : __('Deudor ≠ acreedor')
            }}
          </div>
        </div>
      </div>

      <Tarjeta
        :titulo="__('Saldo final por grupo del PGC')"
        :subtitulo="
          __(
            'Saldos deudores a la derecha y acreedores a la izquierda. Pulse un grupo para filtrar la tabla.',
          )
        "
      >
        <div class="h-[300px] w-full">
          <EChart :option="opcionGrupos" @click="filtrarGrupo" />
        </div>
      </Tarjeta>

      <section
        class="flex min-w-0 flex-col overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:overflow-visible"
      >
        <header
          class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-3 sm:px-5"
        >
          <div>
            <h3 class="text-xl font-semibold text-ink-gray-9">
              {{ __('Balance de sumas y saldos') }}
            </h3>
            <p class="mt-0.5 text-sm text-ink-gray-5">
              {{
                __(
                  'Grupos, subgrupos y cuentas con los nombres del cuadro del PGC. La subcuenta abre su libro mayor.',
                )
              }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Badge
              v-if="grupoFiltro"
              :label="__('Grupo {0}', grupoFiltro)"
              theme="blue"
              variant="subtle"
            />
            <Button
              v-if="grupoFiltro"
              size="sm"
              variant="ghost"
              :label="__('Quitar filtro')"
              @click="grupoFiltro = ''"
            />
          </div>
        </header>
        <div class="overflow-x-auto print:overflow-visible">
          <table class="w-full min-w-[960px] border-collapse text-base">
            <thead>
              <tr
                class="border-b border-outline-gray-1 bg-surface-gray-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
              >
                <th
                  class="sticky left-0 z-10 bg-surface-gray-1 px-4 py-2.5 text-left"
                >
                  {{ __('Cuenta') }}
                </th>
                <th class="px-3 py-2.5 text-right">
                  {{ __('Saldo anterior') }}
                </th>
                <th class="px-3 py-2.5 text-right">{{ __('Debe') }}</th>
                <th class="px-3 py-2.5 text-right">{{ __('Haber') }}</th>
                <th class="px-3 py-2.5 text-right">{{ __('Saldo deudor') }}</th>
                <th class="px-3 py-2.5 text-right">
                  {{ __('Saldo acreedor') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="fila in visibles"
                :key="fila.clave"
                class="group border-b border-outline-gray-1"
                :class="[
                  estilo(fila).fila,
                  fila.account ? 'cursor-pointer' : '',
                ]"
                @click="pulsar(fila)"
              >
                <td
                  class="sticky left-0 z-[1] max-w-[30rem] py-2 pr-3"
                  :class="estilo(fila).celda"
                  :style="{ paddingLeft: `${14 + (fila.nivel - 1) * 18}px` }"
                >
                  <div class="flex min-w-0 items-center gap-1.5">
                    <button
                      v-if="fila.es_grupo && !busqueda"
                      type="button"
                      class="flex size-5 shrink-0 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3 print:hidden"
                      @click.stop="alternar(fila.codigo)"
                    >
                      <LucideChevronRight
                        class="size-3.5 transition-transform"
                        :class="estaAbierto(fila) ? 'rotate-90' : ''"
                      />
                    </button>
                    <span
                      v-else
                      class="inline-block w-5 shrink-0 print:hidden"
                    />
                    <span
                      class="shrink-0 tabular-nums"
                      :class="
                        fila.es_grupo ? 'text-ink-gray-6' : 'text-ink-gray-4'
                      "
                      >{{ fila.codigo }}</span
                    >
                    <span class="truncate" :title="fila.nombre">{{
                      fila.nombre
                    }}</span>
                    <Badge
                      v-if="fila.sintetica"
                      :label="__('calculado')"
                      theme="amber"
                      variant="subtle"
                      size="sm"
                    />
                  </div>
                </td>
                <td
                  class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                  :class="estilo(fila).importe"
                >
                  {{ saldoTexto(fila.saldo_inicial) }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                  :class="estilo(fila).importe"
                >
                  {{ formatImporte(fila.debe) }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                  :class="estilo(fila).importe"
                >
                  {{ formatImporte(fila.haber) }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                  :class="estilo(fila).importe"
                >
                  {{
                    fila.saldo_final > 0.005
                      ? formatImporte(fila.saldo_final)
                      : ''
                  }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-2 text-right tabular-nums"
                  :class="estilo(fila).importe"
                >
                  {{
                    fila.saldo_final < -0.005
                      ? formatImporte(-fila.saldo_final)
                      : ''
                  }}
                </td>
              </tr>
              <tr v-if="!visibles.length">
                <td
                  colspan="6"
                  class="px-4 py-10 text-center text-base text-ink-gray-5"
                >
                  {{ __('Ninguna cuenta coincide') }}
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr
                class="border-t-2 border-outline-gray-3 bg-surface-gray-2 font-semibold text-ink-gray-9"
              >
                <td
                  class="sticky left-0 z-[1] bg-surface-gray-2 px-4 py-3 uppercase tracking-wide"
                >
                  {{ __('Totales') }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-3 text-right text-sm tabular-nums text-ink-gray-6"
                >
                  {{
                    __(
                      'D {0} · H {1}',
                      formatImporte(t.saldo_inicial_deudor),
                      formatImporte(t.saldo_inicial_acreedor),
                    )
                  }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                  {{ formatImporte(t.debe) }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                  {{ formatImporte(t.haber) }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                  {{ formatImporte(t.saldo_deudor) }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                  {{ formatImporte(t.saldo_acreedor) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <p
        v-if="Math.abs(datos.arrastre_resultados) >= 0.005"
        class="text-sm text-ink-gray-6"
      >
        {{
          __(
            'La fila «calculado» recoge {0} de resultados de ejercicios anteriores que siguen en los grupos 6 y 7 porque no tienen asiento de cierre.',
            formatMoney(Math.abs(datos.arrastre_resultados), moneda),
          )
        }}
      </p>
    </template>
  </ReportFrame>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Badge,
  Button,
  Switch,
  TabButtons,
  TextInput,
  createResource,
} from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import KpiCard from '@/components/informes/KpiCard.vue'
import Tarjeta from '@/components/informes/Tarjeta.vue'
import EChart from '@/components/informes/EChart.vue'
import {
  descargarCsv,
  errorMessage,
  etiquetaRango,
  formatCompact,
  formatImporte,
  formatMoney,
  useInformePeriodo,
} from '@/composables/informe'
import { COLOR } from '@/composables/paleta'
import { FUENTE, ejeValor, tooltipBase } from '@/composables/graficos'
import LucideSearch from '~icons/lucide/search'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideCircleAlert from '~icons/lucide/circle-alert'
import LucideArrowDownToLine from '~icons/lucide/arrow-down-to-line'
import LucideArrowUpFromLine from '~icons/lucide/arrow-up-from-line'
import LucidePlus from '~icons/lucide/circle-plus'
import LucideMinus from '~icons/lucide/circle-minus'

const router = useRouter()
const {
  company,
  fromDate,
  toDate,
  companies,
  fiscalYears,
  today,
  contexto,
  whenReady,
} = useInformePeriodo()

const iconos = {
  debe: markRaw(LucideArrowDownToLine),
  haber: markRaw(LucideArrowUpFromLine),
  deudor: markRaw(LucidePlus),
  acreedor: markRaw(LucideMinus),
}

const nivel = ref(3)
const busqueda = ref('')
const soloConSaldo = ref(false)
const grupoFiltro = ref('')
const abiertos = ref(new Set())

const opcionesNivel = [
  { label: __('Grupos'), value: 1 },
  { label: __('Subgrupos'), value: 2 },
  { label: __('Cuentas'), value: 3 },
  { label: __('Subcuentas'), value: 4 },
]

const report = createResource({
  url: 'spain_compliance.api.informes.sumas_y_saldos',
})
const datos = computed(() => report.data || null)
const moneda = computed(() => datos.value?.currency || 'EUR')
const t = computed(() => datos.value?.totales || {})
const cuadra = computed(
  () => datos.value?.cuadre?.sumas && datos.value?.cuadre?.saldos,
)

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
    },
  })
  report.reload()
}
whenReady(load)

const subtitulo = computed(() =>
  etiquetaRango(
    datos.value?.from_date || fromDate.value,
    datos.value?.to_date || toDate.value,
  ),
)
const insignias = computed(() =>
  datos.value
    ? [{ label: __('Ejercicio {0}', datos.value.fiscal_year), theme: 'blue' }]
    : [],
)

function abiertosPorNivel(n) {
  return new Set(
    (datos.value?.filas || [])
      .filter((f) => f.es_grupo && f.nivel < n)
      .map((f) => f.codigo),
  )
}

watch([nivel, datos], () => {
  abiertos.value = abiertosPorNivel(nivel.value)
})

function estaAbierto(fila) {
  return abiertos.value.has(fila.codigo)
}

function alternar(codigo) {
  const nuevos = new Set(abiertos.value)
  if (nuevos.has(codigo)) nuevos.delete(codigo)
  else nuevos.add(codigo)
  abiertos.value = nuevos
}

const filasConClave = computed(() =>
  (datos.value?.filas || []).map((fila, i) => ({
    ...fila,
    clave: `${fila.codigo}-${fila.account || ''}-${i}`,
  })),
)

const padreDeGrupo = computed(
  () =>
    new Map(
      filasConClave.value
        .filter((f) => f.es_grupo)
        .map((f) => [f.codigo, f.padre]),
    ),
)

const visibles = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()
  return filasConClave.value.filter((fila) => {
    if (grupoFiltro.value && !String(fila.codigo).startsWith(grupoFiltro.value))
      return false
    if (soloConSaldo.value && Math.abs(fila.saldo_final) < 0.005) return false
    if (texto) {
      return (
        !fila.es_grupo &&
        (String(fila.codigo).startsWith(texto) ||
          fila.nombre.toLowerCase().includes(texto))
      )
    }
    let padre = fila.padre
    while (padre) {
      if (!abiertos.value.has(padre)) return false
      padre = padreDeGrupo.value.get(padre) || null
    }
    return true
  })
})

function saldoTexto(valor) {
  if (Math.abs(valor) < 0.005) return '—'
  return `${formatImporte(Math.abs(valor))} ${valor > 0 ? 'D' : 'H'}`
}

function estilo(fila) {
  if (fila.nivel === 1)
    return {
      fila: 'bg-surface-gray-1',
      celda:
        'bg-surface-gray-1 font-semibold uppercase tracking-wide text-ink-gray-9',
      importe: 'font-semibold text-ink-gray-9',
    }
  if (fila.nivel === 2)
    return {
      fila: 'hover:bg-surface-gray-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-gray-1 font-semibold text-ink-gray-9',
      importe: 'font-medium text-ink-gray-9',
    }
  if (fila.nivel === 3)
    return {
      fila: 'hover:bg-surface-gray-1',
      celda:
        'bg-surface-elevation-1 group-hover:bg-surface-gray-1 font-medium text-ink-gray-8',
      importe: 'text-ink-gray-8',
    }
  return {
    fila: 'hover:bg-surface-blue-1',
    celda:
      'bg-surface-elevation-1 group-hover:bg-surface-blue-1 text-sm text-ink-gray-6',
    importe: 'text-sm text-ink-gray-6',
  }
}

function pulsar(fila) {
  if (fila.account) {
    router.push({
      name: 'GeneralLedger',
      query: {
        company: company.value,
        from: datos.value.from_date,
        to: datos.value.to_date,
        account: fila.account,
      },
    })
  } else if (fila.es_grupo && !busqueda.value) {
    alternar(fila.codigo)
  }
}

const grupos = computed(() =>
  (datos.value?.filas || []).filter((f) => f.nivel === 1),
)

const opcionGrupos = computed(() => {
  const lista = [...grupos.value].reverse()
  return {
    textStyle: { fontFamily: FUENTE },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: tooltipBase({
      trigger: 'item',
      formatter: (p) => {
        const fila = lista[p.dataIndex]
        return `<b>${fila.codigo} ${fila.nombre}</b><br/>${formatMoney(Math.abs(fila.saldo_final), moneda.value)} ${fila.saldo_final >= 0 ? __('deudor') : __('acreedor')}`
      },
    }),
    xAxis: ejeValor(moneda.value),
    yAxis: {
      type: 'category',
      data: lista.map((f) => `${f.codigo}  ${f.nombre}`),
      axisLabel: {
        color: COLOR.textoSuave,
        fontSize: 11,
        width: 220,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: COLOR.rejilla } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        data: lista.map((f) => ({
          value: f.saldo_final,
          itemStyle: {
            color: f.saldo_final >= 0 ? COLOR.anc : COLOR.pc,
            borderRadius: f.saldo_final >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
            opacity:
              grupoFiltro.value && grupoFiltro.value !== f.codigo ? 0.3 : 1,
          },
        })),
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: COLOR.textoSuave,
          formatter: (p) => formatCompact(p.value, moneda.value),
        },
      },
    ],
  }
})

function filtrarGrupo(params) {
  const fila = [...grupos.value].reverse()[params.dataIndex]
  if (!fila) return
  grupoFiltro.value = grupoFiltro.value === fila.codigo ? '' : fila.codigo
}

function exportar() {
  const d = datos.value
  descargarCsv(
    `sumas-y-saldos-${company.value}-${d.from_date}-${d.to_date}`,
    [
      __('Nivel'),
      __('Cuenta'),
      __('Descripción'),
      __('Saldo anterior'),
      __('Debe'),
      __('Haber'),
      __('Saldo deudor'),
      __('Saldo acreedor'),
    ],
    d.filas.map((f) => [
      f.nivel,
      f.codigo,
      f.nombre,
      f.saldo_inicial,
      f.debe,
      f.haber,
      f.saldo_final > 0 ? f.saldo_final : 0,
      f.saldo_final < 0 ? -f.saldo_final : 0,
    ]),
  )
}
</script>
