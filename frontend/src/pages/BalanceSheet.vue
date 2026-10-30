<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Balance de situación')"
    :subtitle="subtitulo"
    :companies="companies"
    :fiscal-years="fiscalYears"
    :today="today"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(datos)"
    :badges="insignias"
    as-of
    exportable
    @refresh="load"
    @export="exportar"
  >
    <template #filters>
      <CampoFiltro :label="__('Comparar con')">
        <Select v-model="comparar" :options="opcionesComparar" class="w-64" />
      </CampoFiltro>
      <CampoFiltro :label="__('Detalle de la tabla')">
        <TabButtons v-model="detalle" :options="opcionesDetalle" />
      </CampoFiltro>
      <CampoFiltro :label="__('Líneas sin importe')">
        <Switch v-model="mostrarCeros" />
      </CampoFiltro>
    </template>

    <template v-if="datos">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard
          v-for="kpi in kpis"
          :key="kpi.key"
          :label="kpi.label"
          :valor="kpi.valor"
          :titulo="kpi.titulo"
          :delta="kpi.delta"
          :delta-texto="kpi.deltaTexto"
          :pista="kpi.pista"
          :color="kpi.color"
          :icono="kpi.icono"
          :menos-es-mejor="kpi.menosEsMejor"
          :neutro="kpi.neutro"
        />
      </div>

      <div class="grid gap-4 xl:grid-cols-5">
        <Tarjeta
          class="xl:col-span-3"
          :titulo="__('Masas patrimoniales')"
          :subtitulo="
            __(
              'Cómo se financia el activo. La altura de cada bloque es su peso sobre el total.',
            )
          "
        >
          <MasasPatrimoniales
            :masas="datos.masas"
            :periodos="etiquetasPeriodo"
            :currency="datos.currency"
          />
        </Tarjeta>
        <Tarjeta
          class="xl:col-span-2"
          :titulo="__('Salud financiera')"
          :subtitulo="
            __(
              'Ratios de liquidez y endeudamiento frente a rangos de referencia',
            )
          "
        >
          <RatiosSemaforo
            :ratios="datos.ratios"
            :periodos="etiquetasPeriodo"
            :currency="datos.currency"
          />
        </Tarjeta>
      </div>

      <Tarjeta
        :titulo="__('Composición del balance')"
        :subtitulo="
          __('Peso de cada epígrafe y cuenta. Pulse un bloque para ampliarlo.')
        "
      >
        <template v-if="datos.periodos.length > 1" #acciones>
          <TabButtons
            v-model="indiceMapa"
            :options="opcionesPeriodo"
            size="sm"
          />
        </template>
        <ComposicionTreemap
          :activo="datos.activo"
          :pasivo="datos.pasivo"
          :indice="indiceMapa"
          :currency="datos.currency"
        />
      </Tarjeta>

      <div class="grid gap-4">
        <StatementTable
          :titulo="__('Activo')"
          :subtitulo="__('Modelo normal del PGC')"
          :nodos="datos.activo.hijos"
          :total="datos.activo"
          :periodos="etiquetasPeriodo"
          :bases="bases"
          :etiqueta-pct="__('% s/ total')"
          :detalle="detalle"
          :mostrar-ceros="mostrarCeros"
          @cuenta="abrirMayor"
        />
        <StatementTable
          :titulo="__('Patrimonio neto y pasivo')"
          :subtitulo="__('Modelo normal del PGC')"
          :nodos="datos.pasivo.hijos"
          :total="datos.pasivo"
          :periodos="etiquetasPeriodo"
          :bases="bases"
          :etiqueta-pct="__('% s/ total')"
          :detalle="detalle"
          :mostrar-ceros="mostrarCeros"
          @cuenta="abrirMayor"
          @enlace="abrirEnlace"
        />
      </div>

      <div
        class="flex flex-wrap items-center gap-2 text-sm"
        :class="cuadra ? 'text-ink-green-7' : 'text-ink-red-7'"
      >
        <LucideCircleCheck v-if="cuadra" class="size-4" />
        <LucideCircleAlert v-else class="size-4" />
        <span v-if="cuadra">{{
          __(
            'El activo es igual al patrimonio neto más el pasivo en todos los periodos.',
          )
        }}</span>
        <span v-else>{{
          __(
            'Descuadre entre activo y patrimonio neto más pasivo: {0}',
            descuadreTexto,
          )
        }}</span>
      </div>

      <Avisos :avisos="datos.avisos" />
    </template>
  </ReportFrame>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Select, Switch, TabButtons, createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import KpiCard from '@/components/informes/KpiCard.vue'
import Tarjeta from '@/components/informes/Tarjeta.vue'
import StatementTable from '@/components/informes/StatementTable.vue'
import Avisos from '@/components/informes/Avisos.vue'
import MasasPatrimoniales from '@/components/informes/balance/MasasPatrimoniales.vue'
import RatiosSemaforo from '@/components/informes/balance/RatiosSemaforo.vue'
import ComposicionTreemap from '@/components/informes/balance/ComposicionTreemap.vue'
import {
  descargarCsv,
  errorMessage,
  formatCompact,
  formatDate,
  formatMoney,
  formatPct,
  formatRatio,
  useInformePeriodo,
  variacion,
} from '@/composables/informe'
import { aplanarEstado } from '@/composables/estados'
import { COLOR } from '@/composables/paleta'
import LucideLandmark from '~icons/lucide/landmark'
import LucideShield from '~icons/lucide/shield'
import LucideWallet from '~icons/lucide/wallet'
import LucideDroplets from '~icons/lucide/droplets'
import LucideScale from '~icons/lucide/scale'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideCircleAlert from '~icons/lucide/circle-alert'

const router = useRouter()
const {
  company,
  fromDate,
  toDate,
  companies,
  companyInfo,
  fiscalYears,
  today,
  contexto,
  whenReady,
} = useInformePeriodo()

const comparar = ref('cierre')
const detalle = ref('partidas')
const mostrarCeros = ref(false)
const indiceMapa = ref(0)

const opcionesComparar = [
  { label: __('Cierre del ejercicio anterior'), value: 'cierre' },
  { label: __('Misma fecha del año anterior'), value: 'interanual' },
  { label: __('Sin comparar'), value: 'ninguno' },
]
const opcionesDetalle = [
  { label: __('Epígrafes'), value: 'epigrafes' },
  { label: __('Partidas'), value: 'partidas' },
  { label: __('Cuentas'), value: 'cuentas' },
]

const report = createResource({
  url: 'spain_compliance.api.informes.balance_situacion',
})
const datos = computed(() => report.data || null)

function load() {
  report.update({
    params: {
      company: company.value,
      to_date: toDate.value,
      comparar: comparar.value === 'ninguno' ? '' : comparar.value,
    },
  })
  report.reload()
}

whenReady(load)
watch(comparar, () => {
  indiceMapa.value = 0
  if (company.value && toDate.value) load()
})

const etiquetasPeriodo = computed(() =>
  (datos.value?.periodos || []).map((p) => p.label),
)
const opcionesPeriodo = computed(() =>
  etiquetasPeriodo.value.map((label, i) => ({ label, value: i })),
)
const bases = computed(() =>
  (datos.value?.masas || []).map((m) => m.activo || 0),
)

const subtitulo = computed(() => {
  const d = datos.value
  if (!d) return toDate.value ? __('A {0}', formatDate(toDate.value)) : ''
  const [actual, anterior] = d.periodos
  return anterior
    ? __('A {0} frente a {1}', actual.label, anterior.label)
    : __('A {0}', actual.label)
})

const insignias = computed(() => [
  { label: __('PGC · modelo normal'), theme: 'blue' },
  ...(datos.value?.fiscal_year
    ? [{ label: __('Ejercicio {0}', datos.value.fiscal_year) }]
    : []),
])

const cuadra = computed(() =>
  (datos.value?.descuadre || []).every((d) => Math.abs(d) < 0.01),
)
const descuadreTexto = computed(() =>
  (datos.value?.descuadre || [])
    .map((d) => formatMoney(d, datos.value.currency))
    .join(' / '),
)

const kpis = computed(() => {
  const d = datos.value
  if (!d) return []
  const [m, mAnt] = d.masas
  const [r, rAnt] = d.ratios
  const textoAnterior = d.periodos[1] ? __('vs {0}', d.periodos[1].label) : ''
  const delta = (a, b) =>
    b === undefined || b === null ? null : variacion(a, b).pct
  return [
    {
      key: 'activo',
      label: __('Total activo'),
      valor: formatCompact(m.activo, d.currency),
      titulo: formatMoney(m.activo, d.currency),
      delta: mAnt ? delta(m.activo, mAnt.activo) : null,
      deltaTexto: textoAnterior,
      neutro: true,
      color: COLOR.anc,
      icono: markRaw(LucideLandmark),
      pista: __(
        'No corriente {0} · corriente {1}',
        formatPct(m.activo ? m.anc / m.activo : null),
        formatPct(m.activo ? m.ac / m.activo : null),
      ),
    },
    {
      key: 'pn',
      label: __('Patrimonio neto'),
      valor: formatCompact(m.pn, d.currency),
      titulo: formatMoney(m.pn, d.currency),
      delta: mAnt ? delta(m.pn, mAnt.pn) : null,
      deltaTexto: textoAnterior,
      color: COLOR.pn,
      icono: markRaw(LucideShield),
      pista: __(
        '{0} del total financiado con recursos propios',
        formatPct(m.activo ? m.pn / m.activo : null),
      ),
    },
    {
      key: 'fm',
      label: __('Fondo de maniobra'),
      valor: formatCompact(r.fondo_maniobra, d.currency),
      titulo: formatMoney(r.fondo_maniobra, d.currency),
      delta: rAnt ? delta(r.fondo_maniobra, rAnt.fondo_maniobra) : null,
      deltaTexto: textoAnterior,
      color: r.fondo_maniobra >= 0 ? COLOR.disponible : COLOR.pc,
      icono: markRaw(LucideWallet),
      pista:
        r.fondo_maniobra >= 0
          ? __('Circulante suficiente')
          : __('Tensión de liquidez'),
    },
    {
      key: 'liquidez',
      label: __('Liquidez general'),
      valor: formatRatio(r.liquidez),
      delta: rAnt ? delta(r.liquidez, rAnt.liquidez) : null,
      deltaTexto: textoAnterior,
      color: COLOR.existencias,
      icono: markRaw(LucideDroplets),
      pista: __('Prueba ácida {0}', formatRatio(r.acida)),
    },
    {
      key: 'endeudamiento',
      label: __('Endeudamiento'),
      valor: formatPct(r.endeudamiento),
      delta: rAnt ? delta(r.endeudamiento, rAnt.endeudamiento) : null,
      deltaTexto: textoAnterior,
      menosEsMejor: true,
      color: COLOR.pnc,
      icono: markRaw(LucideScale),
      pista: __('Solvencia {0}', formatRatio(r.solvencia)),
    },
  ]
})

function abrirMayor(cuenta) {
  router.push({
    name: 'GeneralLedger',
    query: {
      company: company.value,
      from: datos.value.from_date,
      to: datos.value.to_date,
      account: cuenta.account,
    },
  })
}

function abrirEnlace(enlace) {
  if (enlace !== 'pyg') return
  router.push({
    name: 'ProfitAndLoss',
    query: {
      company: company.value,
      from: datos.value.from_date,
      to: datos.value.to_date,
    },
  })
}

function exportar() {
  const d = datos.value
  const filas = [...aplanarEstado([d.activo]), ...aplanarEstado([d.pasivo])]
  descargarCsv(
    `balance-${company.value}-${d.to_date}`,
    [__('Código'), __('Concepto'), ...etiquetasPeriodo.value],
    filas.map((fila) => [fila.codigo, fila.concepto, ...fila.importes]),
  )
}
</script>
