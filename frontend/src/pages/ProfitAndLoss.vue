<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Pérdidas y ganancias')"
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
      <CampoFiltro :label="__('Comparar con el año anterior')">
        <Switch v-model="comparar" />
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
          :valor="formatCompact(kpi.valor, datos.currency)"
          :titulo="formatMoney(kpi.valor, datos.currency)"
          :delta="kpi.delta"
          :delta-texto="kpi.deltaTexto"
          :pista="kpi.pista"
          :serie="kpi.serie"
          :color="kpi.color"
          :icono="kpi.icono"
        />
      </div>

      <div class="grid gap-4 xl:grid-cols-3">
        <Tarjeta
          class="xl:col-span-2"
          :titulo="__('Cascada de resultados')"
          :subtitulo="
            __(
              'Cómo se pasa de la cifra de negocios al resultado del ejercicio',
            )
          "
        >
          <template v-if="datos.periodos.length > 1" #acciones>
            <TabButtons
              v-model="indiceGrafico"
              :options="opcionesPeriodo"
              size="sm"
            />
          </template>
          <CascadaPyG
            :lineas="datos.lineas"
            :indice="indiceGrafico"
            :currency="datos.currency"
          />
        </Tarjeta>
        <Tarjeta
          :titulo="__('De cada 100 € de ingresos')"
          :subtitulo="__('Reparto de los ingresos entre gastos y beneficio')"
        >
          <CienEuros
            :lineas="datos.lineas"
            :indice="indiceGrafico"
            :currency="datos.currency"
          />
        </Tarjeta>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <Tarjeta
          :titulo="__('Flujo de ingresos y gastos')"
          :subtitulo="__('De dónde viene cada euro y a qué se destina')"
        >
          <FlujoPyG
            :lineas="datos.lineas"
            :indice="indiceGrafico"
            :currency="datos.currency"
          />
        </Tarjeta>
        <Tarjeta
          :titulo="__('Evolución mensual')"
          :subtitulo="
            __(
              'Cifra de negocios, gastos y resultado acumulado frente al año anterior',
            )
          "
        >
          <EvolucionPyG
            :meses="datos.meses"
            :mensual="datos.mensual"
            :periodos="etiquetasPeriodo"
            :currency="datos.currency"
          />
        </Tarjeta>
      </div>

      <StatementTable
        :titulo="__('Cuenta de pérdidas y ganancias')"
        :subtitulo="
          __(
            'Modelo normal del PGC. Despliegue cualquier línea hasta la subcuenta; la subcuenta abre su libro mayor.',
          )
        "
        :nodos="datos.lineas"
        :periodos="etiquetasPeriodo"
        :bases="bases"
        :etiqueta-pct="__('% s/ cifra')"
        :detalle="detalle"
        :mostrar-ceros="mostrarCeros"
        :mensual="datos.mensual[0]"
        tono="pyg"
        @cuenta="abrirMayor"
      />

      <Avisos :avisos="datos.avisos" />
    </template>
  </ReportFrame>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Switch, TabButtons, createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import KpiCard from '@/components/informes/KpiCard.vue'
import Tarjeta from '@/components/informes/Tarjeta.vue'
import StatementTable from '@/components/informes/StatementTable.vue'
import Avisos from '@/components/informes/Avisos.vue'
import CascadaPyG from '@/components/informes/pyg/CascadaPyG.vue'
import FlujoPyG from '@/components/informes/pyg/FlujoPyG.vue'
import CienEuros from '@/components/informes/pyg/CienEuros.vue'
import EvolucionPyG from '@/components/informes/pyg/EvolucionPyG.vue'
import {
  descargarCsv,
  errorMessage,
  etiquetaRango,
  formatCompact,
  formatMoney,
  formatPct,
  useInformePeriodo,
  variacion,
} from '@/composables/informe'
import { aplanarEstado } from '@/composables/estados'
import LucideReceiptEuro from '~icons/lucide/receipt-euro'
import LucidePackage from '~icons/lucide/package'
import LucideActivity from '~icons/lucide/activity'
import LucideFactory from '~icons/lucide/factory'
import LucideTrophy from '~icons/lucide/trophy'

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

const comparar = ref(true)
const detalle = ref('partidas')
const mostrarCeros = ref(false)
const indiceGrafico = ref(0)

const opcionesDetalle = [
  { label: __('Epígrafes'), value: 'epigrafes' },
  { label: __('Partidas'), value: 'partidas' },
  { label: __('Cuentas'), value: 'cuentas' },
]

const report = createResource({
  url: 'spain_compliance.api.informes.perdidas_y_ganancias',
})
const datos = computed(() => report.data || null)

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
      comparar: comparar.value ? 1 : 0,
    },
  })
  report.reload()
}

whenReady(load)
watch(comparar, () => {
  indiceGrafico.value = 0
  if (company.value && fromDate.value && toDate.value) load()
})

const etiquetasPeriodo = computed(() =>
  (datos.value?.periodos || []).map((p) => p.label),
)
const opcionesPeriodo = computed(() =>
  etiquetasPeriodo.value.map((label, i) => ({ label, value: i })),
)

const subtitulo = computed(() => {
  if (!datos.value) return etiquetaRango(fromDate.value, toDate.value)
  const [actual, anterior] = datos.value.periodos
  const texto = etiquetaRango(actual.desde, actual.hasta)
  return anterior
    ? __(
        '{0} frente a {1}',
        texto,
        etiquetaRango(anterior.desde, anterior.hasta),
      )
    : texto
})

const insignias = computed(() => [
  { label: __('PGC · modelo normal'), theme: 'blue' },
  ...(companyInfo.value?.modelo
    ? [{ label: __('Cuentas anuales: {0}', companyInfo.value.modelo) }]
    : []),
])

const bases = computed(() =>
  (datos.value?.kpis || []).map((k) => k.cifra_negocios || k.ingresos || 0),
)

function serieMensual(code) {
  return datos.value?.mensual?.[0]?.[code] || null
}

function sumaSeries(...series) {
  const validas = series.filter(Boolean)
  if (!validas.length) return null
  return validas[0].map((_, i) =>
    validas.reduce((s, serie) => s + (serie[i] || 0), 0),
  )
}

const kpis = computed(() => {
  const d = datos.value
  if (!d) return []
  const [actual, anterior] = d.kpis
  const textoAnterior = d.periodos[1] ? __('vs {0}', d.periodos[1].label) : ''
  const margen = (valor) =>
    actual.cifra_negocios ? valor / actual.cifra_negocios : null
  const tarjeta = (key, label, valor, color, icono, pista, serie) => ({
    key,
    label,
    valor,
    color,
    icono: markRaw(icono),
    pista,
    serie,
    delta: anterior ? variacion(valor, anterior[key]).pct : null,
    deltaTexto: textoAnterior,
  })
  const ebitdaMensual = sumaSeries(
    serieMensual('A.1'),
    (serieMensual('8') || []).map((v) => -v),
    (serieMensual('11') || []).map((v) => -v),
  )
  return [
    tarjeta(
      'cifra_negocios',
      __('Cifra de negocios'),
      actual.cifra_negocios,
      '#10B981',
      LucideReceiptEuro,
      '',
      serieMensual('1'),
    ),
    tarjeta(
      'margen_bruto',
      __('Margen bruto'),
      actual.margen_bruto,
      '#0EA5E9',
      LucidePackage,
      margen(actual.margen_bruto) !== null
        ? __(
            '{0} de la cifra de negocios',
            formatPct(margen(actual.margen_bruto)),
          )
        : '',
      sumaSeries(serieMensual('1'), serieMensual('2'), serieMensual('4')),
    ),
    tarjeta(
      'ebitda',
      __('EBITDA'),
      actual.ebitda,
      '#8B5CF6',
      LucideActivity,
      margen(actual.ebitda) !== null
        ? __('Margen {0}', formatPct(margen(actual.ebitda)))
        : '',
      ebitdaMensual,
    ),
    tarjeta(
      'resultado_explotacion',
      __('Resultado de explotación'),
      actual.resultado_explotacion,
      '#F59E0B',
      LucideFactory,
      margen(actual.resultado_explotacion) !== null
        ? __('Margen {0}', formatPct(margen(actual.resultado_explotacion)))
        : '',
      serieMensual('A.1'),
    ),
    tarjeta(
      'resultado',
      __('Resultado del ejercicio'),
      actual.resultado,
      actual.resultado >= 0 ? '#059669' : '#E11D48',
      LucideTrophy,
      margen(actual.resultado) !== null
        ? __('Margen neto {0}', formatPct(margen(actual.resultado)))
        : '',
      serieMensual('A.5'),
    ),
  ]
})

function abrirMayor(cuenta) {
  router.push({
    name: 'GeneralLedger',
    query: {
      company: company.value,
      from: datos.value.periodos[0].desde,
      to: datos.value.periodos[0].hasta,
      account: cuenta.account,
    },
  })
}

function exportar() {
  const d = datos.value
  const cabeceras = [__('Código'), __('Concepto'), ...etiquetasPeriodo.value]
  descargarCsv(
    `perdidas-y-ganancias-${company.value}-${d.from_date}-${d.to_date}`,
    cabeceras,
    aplanarEstado(d.lineas).map((fila) => [
      fila.codigo,
      fila.concepto,
      ...fila.importes,
    ]),
  )
}
</script>
