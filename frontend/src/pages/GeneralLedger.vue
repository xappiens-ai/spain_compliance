<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Libro mayor')"
    :subtitle="subtitulo"
    :companies="companies"
    :fiscal-years="fiscalYears"
    :today="today"
    :loading="report.loading || contexto.loading"
    :error="errorMessage(report.error)"
    :has-data="Boolean(datos)"
    exportable
    @refresh="load"
    @export="exportar"
  >
    <template #filters>
      <CampoFiltro v-if="company" :label="__('Cuenta')">
        <div class="flex items-center gap-1">
          <AccountPicker v-model="cuenta" :company="company" />
          <Button
            variant="ghost"
            :disabled="!anterior"
            :tooltip="anterior ? `${anterior.numero} ${anterior.nombre}` : ''"
            @click="cuenta = anterior.account"
          >
            <template #icon><LucideChevronLeft class="size-4" /></template>
          </Button>
          <Button
            variant="ghost"
            :disabled="!siguiente"
            :tooltip="
              siguiente ? `${siguiente.numero} ${siguiente.nombre}` : ''
            "
            @click="cuenta = siguiente.account"
          >
            <template #icon><LucideChevronRight class="size-4" /></template>
          </Button>
        </div>
      </CampoFiltro>
      <CampoFiltro :label="__('Filtrar movimientos')">
        <TextInput
          v-model="busqueda"
          :placeholder="__('Documento, concepto, tercero…')"
          class="w-64"
          :debounce="200"
        >
          <template #prefix
            ><LucideSearch class="size-4 text-ink-gray-5"
          /></template>
        </TextInput>
      </CampoFiltro>
    </template>

    <template v-if="datos">
      <template v-if="unaCuenta">
        <section
          class="overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1"
        >
          <div
            class="flex flex-wrap items-start justify-between gap-4 border-b border-outline-gray-1 px-5 py-4"
          >
            <div class="min-w-0">
              <div
                v-if="unaCuenta.ruta.length"
                class="mb-1 flex flex-wrap items-center gap-1 text-xs text-ink-gray-5"
              >
                <template
                  v-for="(paso, i) in unaCuenta.ruta"
                  :key="paso.codigo"
                >
                  <LucideChevronRight v-if="i" class="size-3" />
                  <span
                    ><span class="tabular-nums">{{ paso.codigo }}</span>
                    {{ paso.nombre }}</span
                  >
                </template>
              </div>
              <h2
                class="flex flex-wrap items-baseline gap-x-3 text-4xl font-semibold text-ink-gray-9"
              >
                <span class="tabular-nums text-ink-gray-5">{{
                  unaCuenta.numero
                }}</span>
                <span class="min-w-0 truncate">{{ unaCuenta.nombre }}</span>
              </h2>
            </div>
            <Badge
              :label="
                unaCuenta.saldo_final >= 0
                  ? __('Saldo deudor')
                  : __('Saldo acreedor')
              "
              :theme="unaCuenta.saldo_final >= 0 ? 'blue' : 'violet'"
              variant="subtle"
              size="lg"
            />
          </div>
          <div
            class="grid grid-cols-2 divide-x divide-outline-gray-1 sm:grid-cols-5"
          >
            <div
              v-for="dato in resumenCuenta"
              :key="dato.label"
              class="px-5 py-3"
            >
              <div
                class="text-xs font-medium uppercase tracking-wide text-ink-gray-5"
              >
                {{ dato.label }}
              </div>
              <div
                class="mt-1 text-2xl font-semibold tabular-nums"
                :class="dato.clase || 'text-ink-gray-9'"
              >
                {{ dato.valor }}
              </div>
            </div>
          </div>
        </section>

        <Tarjeta
          v-if="datos.serie?.length"
          :titulo="__('Evolución del saldo')"
          :subtitulo="__('Saldo diario y movimientos del mes')"
        >
          <EvolucionSaldo
            :serie="datos.serie"
            :saldo-inicial="unaCuenta.saldo_inicial"
            :desde="datos.from_date"
            :currency="datos.currency"
          />
        </Tarjeta>

        <section
          class="overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:overflow-visible"
        >
          <MovimientosMayor :cuenta="unaCuenta" :busqueda="busqueda" />
        </section>
      </template>

      <template v-else>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            :label="__('Cuentas con movimientos')"
            :valor="formatNumber(datos.totales.cuentas, 0)"
            :color="COLOR.anc"
            :icono="iconos.cuentas"
          />
          <KpiCard
            :label="__('Movimientos')"
            :valor="formatNumber(datos.totales.movimientos, 0)"
            :color="COLOR.existencias"
            :icono="iconos.movimientos"
          />
          <KpiCard
            :label="__('Total debe')"
            :valor="formatCompact(datos.totales.debe, moneda)"
            :titulo="formatMoney(datos.totales.debe, moneda)"
            :color="COLOR.realizable"
            :icono="iconos.debe"
          />
          <KpiCard
            :label="__('Total haber')"
            :valor="formatCompact(datos.totales.haber, moneda)"
            :titulo="formatMoney(datos.totales.haber, moneda)"
            :color="COLOR.pn"
            :icono="iconos.haber"
          />
        </div>

        <details
          v-for="(item, i) in datos.cuentas"
          :key="item.account"
          :open="datos.cuentas.length <= 3 || i === 0"
          class="group overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:break-inside-avoid"
        >
          <summary
            class="flex cursor-pointer list-none flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3 hover:bg-surface-gray-1"
          >
            <div class="flex min-w-0 flex-1 items-center gap-2">
              <LucideChevronRight
                class="size-4 shrink-0 text-ink-gray-5 transition-transform group-open:rotate-90"
              />
              <span class="tabular-nums text-ink-gray-5">{{
                item.numero
              }}</span>
              <span class="truncate text-lg font-semibold text-ink-gray-9">{{
                item.nombre
              }}</span>
              <Button
                size="sm"
                variant="ghost"
                :label="__('Ver cuenta')"
                class="print:hidden"
                @click.prevent="cuenta = item.account"
              />
            </div>
            <div
              class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm tabular-nums"
            >
              <span class="text-ink-gray-5"
                >{{ __('Anterior') }}
                <b class="font-medium text-ink-gray-8">{{
                  saldo(item.saldo_inicial)
                }}</b></span
              >
              <span class="text-ink-gray-5"
                >{{ __('Debe') }}
                <b class="font-medium text-ink-gray-8">{{
                  formatImporte(item.debe)
                }}</b></span
              >
              <span class="text-ink-gray-5"
                >{{ __('Haber') }}
                <b class="font-medium text-ink-gray-8">{{
                  formatImporte(item.haber)
                }}</b></span
              >
              <span class="text-ink-gray-5"
                >{{ __('Final') }}
                <b class="font-semibold text-ink-gray-9">{{
                  saldo(item.saldo_final)
                }}</b></span
              >
              <Badge
                :label="__('{0} mov.', formatNumber(item.n_movimientos, 0))"
                variant="subtle"
              />
            </div>
          </summary>
          <div class="border-t border-outline-gray-1">
            <MovimientosMayor :cuenta="item" :busqueda="busqueda" />
          </div>
        </details>
        <div
          v-if="!datos.cuentas.length"
          class="rounded-xl border border-outline-gray-1 bg-surface-elevation-1 px-4 py-12 text-center text-base text-ink-gray-5"
        >
          {{ __('Sin movimientos en el periodo') }}
        </div>

        <Paginacion
          v-model:page="pagina"
          v-model:page-size="tamano"
          :paginas="datos.pagination.pages"
          :total="datos.pagination.total"
          :etiqueta="__('cuentas')"
          :tamanos="[10, 20, 50]"
        />
      </template>
    </template>
  </ReportFrame>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Badge, Button, TextInput, createResource } from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import KpiCard from '@/components/informes/KpiCard.vue'
import Tarjeta from '@/components/informes/Tarjeta.vue'
import AccountPicker from '@/components/informes/AccountPicker.vue'
import Paginacion from '@/components/informes/Paginacion.vue'
import MovimientosMayor from '@/components/informes/MovimientosMayor.vue'
import EvolucionSaldo from '@/components/informes/EvolucionSaldo.vue'
import {
  descargarCsv,
  errorMessage,
  etiquetaRango,
  formatCompact,
  formatDate,
  formatImporte,
  formatMoney,
  formatNumber,
  useInformePeriodo,
} from '@/composables/informe'
import { COLOR } from '@/composables/paleta'
import LucideSearch from '~icons/lucide/search'
import LucideChevronLeft from '~icons/lucide/chevron-left'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideLayers from '~icons/lucide/layers'
import LucideList from '~icons/lucide/list'
import LucideArrowDownToLine from '~icons/lucide/arrow-down-to-line'
import LucideArrowUpFromLine from '~icons/lucide/arrow-up-from-line'

const route = useRoute()
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
  cuentas: markRaw(LucideLayers),
  movimientos: markRaw(LucideList),
  debe: markRaw(LucideArrowDownToLine),
  haber: markRaw(LucideArrowUpFromLine),
}

const cuenta = ref(route.query.account || '')
const busqueda = ref('')
const pagina = ref(1)
const tamano = ref(20)

const report = createResource({
  url: 'spain_compliance.api.informes.libro_mayor',
})
const conMovimiento = createResource({
  url: 'spain_compliance.api.informes.cuentas_con_movimiento',
})
const datos = computed(() => report.data || null)
const moneda = computed(() => datos.value?.currency || 'EUR')

function load() {
  report.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
      account: cuenta.value || undefined,
      page: pagina.value,
      page_size: tamano.value,
    },
  })
  report.reload()
  conMovimiento.update({
    params: {
      company: company.value,
      from_date: fromDate.value,
      to_date: toDate.value,
    },
  })
  conMovimiento.reload()
}

whenReady(load)
watch([cuenta, tamano], () => {
  if (pagina.value !== 1) pagina.value = 1
  else if (company.value) load()
})
watch(pagina, () => company.value && load())
watch(company, (_nueva, anterior) => {
  if (anterior) cuenta.value = ''
})

const unaCuenta = computed(() => {
  const d = datos.value
  if (!d || !cuenta.value || d.cuentas.length !== 1) return null
  return d.cuentas[0]
})

const posicion = computed(() =>
  (conMovimiento.data || []).findIndex((c) => c.account === cuenta.value),
)
const anterior = computed(() =>
  posicion.value > 0 ? conMovimiento.data[posicion.value - 1] : null,
)
const siguiente = computed(() => {
  const lista = conMovimiento.data || []
  if (!cuenta.value) return null
  return posicion.value >= 0 && posicion.value < lista.length - 1
    ? lista[posicion.value + 1]
    : null
})

const subtitulo = computed(() =>
  etiquetaRango(
    datos.value?.from_date || fromDate.value,
    datos.value?.to_date || toDate.value,
  ),
)

function saldo(valor) {
  const v = Number(valor) || 0
  if (Math.abs(v) < 0.005) return '0,00'
  return `${formatImporte(Math.abs(v))} ${v > 0 ? 'D' : 'H'}`
}

const resumenCuenta = computed(() => {
  const c = unaCuenta.value
  if (!c) return []
  return [
    {
      label: c.pyg ? __('Saldo inicial del ejercicio') : __('Saldo anterior'),
      valor: saldo(c.saldo_inicial),
    },
    {
      label: __('Debe'),
      valor: formatImporte(c.debe),
      clase: 'text-ink-green-7',
    },
    {
      label: __('Haber'),
      valor: formatImporte(c.haber),
      clase: 'text-ink-red-7',
    },
    { label: __('Saldo final'), valor: saldo(c.saldo_final) },
    { label: __('Movimientos'), valor: formatNumber(c.n_movimientos, 0) },
  ]
})

function exportar() {
  const d = datos.value
  const filas = []
  for (const c of d.cuentas) {
    filas.push([
      c.numero,
      c.nombre,
      '',
      '',
      '',
      __('Saldo anterior'),
      '',
      '',
      '',
      c.saldo_inicial,
    ])
    for (const m of c.movimientos) {
      filas.push([
        c.numero,
        c.nombre,
        formatDate(m.posting_date),
        m.asiento || '',
        m.voucher_no,
        m.concepto,
        m.contrapartida,
        m.debit,
        m.credit,
        m.balance,
      ])
    }
  }
  descargarCsv(
    `libro-mayor-${company.value}-${d.from_date}-${d.to_date}${d.pagination.pages > 1 ? `-p${d.pagination.page}` : ''}`,
    [
      __('Cuenta'),
      __('Descripción'),
      __('Fecha'),
      __('Asiento'),
      __('Documento'),
      __('Concepto'),
      __('Contrapartida'),
      __('Debe'),
      __('Haber'),
      __('Saldo'),
    ],
    filas,
  )
}
</script>
