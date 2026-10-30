<template>
  <ReportFrame
    v-model:company="company"
    v-model:from-date="fromDate"
    v-model:to-date="toDate"
    :title="__('Libro diario')"
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
      <CampoFiltro :label="__('Buscar')">
        <TextInput
          v-model="busqueda"
          :placeholder="__('Documento, concepto, cuenta…')"
          class="w-64"
          :debounce="400"
        >
          <template #prefix
            ><LucideSearch class="size-4 text-ink-gray-5"
          /></template>
        </TextInput>
      </CampoFiltro>
      <CampoFiltro :label="__('Tipo de documento')">
        <Select v-model="tipo" :options="opcionesTipo" class="w-52" />
      </CampoFiltro>
      <CampoFiltro :label="__('Clase')">
        <Select v-model="clase" :options="opcionesClase" class="w-40" />
      </CampoFiltro>
      <CampoFiltro v-if="company" :label="__('Cuenta')">
        <AccountPicker v-model="cuenta" :company="company" />
      </CampoFiltro>
    </template>

    <template v-if="datos">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          :label="__('Asientos')"
          :valor="formatNumber(datos.totals.asientos, 0)"
          :pista="
            filtrado
              ? __(
                  'de {0} en el periodo',
                  formatNumber(datos.totals.asientos_periodo, 0),
                )
              : __(
                  'Numeración correlativa del ejercicio {0}',
                  datos.fiscal_year,
                )
          "
          :color="COLOR.anc"
          :icono="iconos.asientos"
        />
        <KpiCard
          :label="__('Total debe')"
          :valor="formatCompact(datos.totals.debe, moneda)"
          :titulo="formatMoney(datos.totals.debe, moneda)"
          :color="COLOR.realizable"
          :icono="iconos.debe"
        />
        <KpiCard
          :label="__('Total haber')"
          :valor="formatCompact(datos.totals.haber, moneda)"
          :titulo="formatMoney(datos.totals.haber, moneda)"
          :color="COLOR.pn"
          :icono="iconos.haber"
        />
        <div
          class="flex flex-col justify-center gap-2 rounded-xl border p-4"
          :class="
            datos.cuadrado
              ? 'border-outline-green-2 bg-surface-green-1'
              : 'border-outline-red-2 bg-surface-red-1'
          "
        >
          <div
            class="flex items-center gap-2 text-lg font-semibold"
            :class="datos.cuadrado ? 'text-ink-green-8' : 'text-ink-red-8'"
          >
            <LucideCircleCheck v-if="datos.cuadrado" class="size-5" />
            <LucideCircleAlert v-else class="size-5" />
            {{
              datos.cuadrado
                ? __('Debe y haber cuadran')
                : __('Debe y haber no cuadran')
            }}
          </div>
          <div class="text-sm text-ink-gray-7">
            {{
              __(
                'Diferencia {0}',
                formatMoney(datos.totals.debe - datos.totals.haber, moneda),
              )
            }}
          </div>
        </div>
      </div>

      <div
        v-if="datos.tipos.length > 1"
        class="flex flex-wrap items-center gap-2 print:hidden"
      >
        <span class="text-sm text-ink-gray-5">{{ __('Por tipo:') }}</span>
        <Button
          v-for="item in datos.tipos"
          :key="item.value"
          size="sm"
          :variant="tipo === item.value ? 'solid' : 'subtle'"
          :label="`${item.label} · ${formatNumber(item.asientos, 0)}`"
          @click="tipo = tipo === item.value ? '' : item.value"
        />
      </div>

      <section
        class="overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-elevation-1 print:overflow-visible"
      >
        <div class="overflow-x-auto print:overflow-visible">
          <table class="w-full min-w-[960px] border-collapse text-base">
            <thead class="sticky top-0 z-10">
              <tr
                class="border-b border-outline-gray-1 bg-surface-gray-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
              >
                <th class="w-20 px-4 py-2.5 text-left">{{ __('Asiento') }}</th>
                <th class="w-36 px-3 py-2.5 text-left">{{ __('Cuenta') }}</th>
                <th class="px-3 py-2.5 text-left">{{ __('Descripción') }}</th>
                <th class="px-3 py-2.5 text-left">{{ __('Concepto') }}</th>
                <th class="w-36 px-3 py-2.5 text-right">{{ __('Debe') }}</th>
                <th class="w-36 px-4 py-2.5 text-right">{{ __('Haber') }}</th>
              </tr>
            </thead>
            <tbody
              v-for="asiento in datos.entries"
              :key="asiento.voucher_type + asiento.voucher_no"
              class="border-b-2 border-outline-gray-2 print:break-inside-avoid"
            >
              <tr class="bg-surface-gray-1">
                <td colspan="6" class="px-4 py-2">
                  <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span class="flex items-center gap-2">
                      <Badge
                        :label="String(asiento.numero)"
                        theme="gray"
                        variant="solid"
                        size="lg"
                      />
                      <span
                        class="text-sm font-medium tabular-nums text-ink-gray-8"
                        >{{ formatDate(asiento.posting_date) }}</span
                      >
                    </span>
                    <Badge
                      :label="asiento.voucher_subtype || asiento.voucher_label"
                      :theme="temaTipo(asiento.voucher_type)"
                      variant="subtle"
                    />
                    <Badge
                      v-if="asiento.clase !== 'Diario'"
                      :label="asiento.clase"
                      :theme="asiento.clase === 'Apertura' ? 'blue' : 'orange'"
                      variant="subtle"
                    />
                    <button
                      type="button"
                      class="inline-flex items-center gap-1 text-sm font-medium text-ink-gray-8 hover:text-ink-blue-7 hover:underline"
                      @click="
                        openDesk(asiento.voucher_type, asiento.voucher_no)
                      "
                    >
                      {{ asiento.voucher_no }}
                      <LucideExternalLink class="size-3.5 print:hidden" />
                    </button>
                    <span
                      v-if="asiento.tercero"
                      class="truncate text-sm text-ink-gray-6"
                      >· {{ asiento.tercero }}</span
                    >
                    <span
                      v-if="asiento.concepto"
                      class="min-w-0 flex-1 truncate text-sm text-ink-gray-5"
                      :title="asiento.concepto"
                    >
                      {{ asiento.concepto }}
                    </span>
                  </div>
                </td>
              </tr>
              <tr
                v-for="linea in asiento.lines"
                :key="linea.name"
                class="border-t border-outline-gray-1 hover:bg-surface-gray-1"
              >
                <td class="px-4 py-1.5" />
                <td class="whitespace-nowrap px-3 py-1.5 tabular-nums">
                  <button
                    type="button"
                    class="text-ink-gray-7 hover:text-ink-blue-7 hover:underline"
                    @click="abrirMayor(linea.account)"
                  >
                    {{ linea.account_number || '—' }}
                  </button>
                </td>
                <td
                  class="max-w-xs truncate px-3 py-1.5 text-ink-gray-8"
                  :class="linea.credit && !linea.debit ? 'pl-8' : ''"
                  :title="linea.account_name"
                >
                  {{ linea.account_name }}
                </td>
                <td
                  class="max-w-sm truncate px-3 py-1.5 text-sm text-ink-gray-5"
                  :title="linea.concepto"
                >
                  {{ linea.concepto }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-ink-gray-9"
                >
                  {{ linea.debit ? formatImporte(linea.debit) : '' }}
                </td>
                <td
                  class="whitespace-nowrap px-4 py-1.5 text-right tabular-nums text-ink-gray-9"
                >
                  {{ linea.credit ? formatImporte(linea.credit) : '' }}
                </td>
              </tr>
              <tr
                v-if="asiento.lines.length > 2"
                class="border-t border-outline-gray-1 text-sm"
              >
                <td colspan="4" class="px-4 py-1.5 text-right text-ink-gray-5">
                  {{ __('Total asiento {0}', asiento.numero) }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-1.5 text-right font-medium tabular-nums text-ink-gray-7"
                >
                  {{ formatImporte(asiento.debit) }}
                </td>
                <td
                  class="whitespace-nowrap px-4 py-1.5 text-right font-medium tabular-nums text-ink-gray-7"
                >
                  {{ formatImporte(asiento.credit) }}
                </td>
              </tr>
            </tbody>
            <tbody v-if="!datos.entries.length">
              <tr>
                <td
                  colspan="6"
                  class="px-4 py-12 text-center text-base text-ink-gray-5"
                >
                  {{ __('Sin asientos con estos filtros') }}
                </td>
              </tr>
            </tbody>
            <tfoot v-if="datos.entries.length">
              <tr
                class="border-t-2 border-outline-gray-3 bg-surface-gray-2 font-semibold text-ink-gray-9"
              >
                <td
                  colspan="4"
                  class="px-4 py-3 text-right uppercase tracking-wide"
                >
                  {{
                    datos.pagination.pages > 1
                      ? __('Total filtrado (todas las páginas)')
                      : __('Total del periodo')
                  }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                  {{ formatImporte(datos.totals.debe) }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                  {{ formatImporte(datos.totals.haber) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <Paginacion
        v-model:page="pagina"
        v-model:page-size="tamano"
        :paginas="datos.pagination.pages"
        :total="datos.pagination.total"
        :etiqueta="__('asientos')"
        :tamanos="[25, 50, 100, 200]"
      />
    </template>
  </ReportFrame>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Badge,
  Button,
  Select,
  TextInput,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import ReportFrame from '@/components/ReportFrame.vue'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import KpiCard from '@/components/informes/KpiCard.vue'
import AccountPicker from '@/components/informes/AccountPicker.vue'
import Paginacion from '@/components/informes/Paginacion.vue'
import {
  descargarCsv,
  errorMessage,
  etiquetaRango,
  formatCompact,
  formatDate,
  formatImporte,
  formatMoney,
  formatNumber,
  openDesk,
  useInformePeriodo,
} from '@/composables/informe'
import { COLOR } from '@/composables/paleta'
import LucideSearch from '~icons/lucide/search'
import LucideExternalLink from '~icons/lucide/external-link'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideCircleAlert from '~icons/lucide/circle-alert'
import LucideBookOpen from '~icons/lucide/book-open'
import LucideArrowDownToLine from '~icons/lucide/arrow-down-to-line'
import LucideArrowUpFromLine from '~icons/lucide/arrow-up-from-line'

const route = useRoute()
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
  asientos: markRaw(LucideBookOpen),
  debe: markRaw(LucideArrowDownToLine),
  haber: markRaw(LucideArrowUpFromLine),
}

const busqueda = ref('')
const tipo = ref('')
const clase = ref('')
const cuenta = ref(route.query.account || '')
const pagina = ref(1)
const tamano = ref(50)

const report = createResource({
  url: 'spain_compliance.api.informes.libro_diario',
})
const datos = computed(() => report.data || null)
const moneda = computed(() => datos.value?.currency || 'EUR')
const filtrado = computed(() =>
  Boolean(busqueda.value || tipo.value || clase.value || cuenta.value),
)

const TEMAS_TIPO = {
  'Sales Invoice': 'green',
  'Purchase Invoice': 'orange',
  'Payment Entry': 'blue',
  'Journal Entry': 'violet',
  'Period Closing Voucher': 'red',
  'Delivery Note': 'green',
  'Purchase Receipt': 'amber',
}

function temaTipo(voucherType) {
  return TEMAS_TIPO[voucherType] || 'gray'
}

const opcionesTipo = computed(() => [
  { label: __('Todos'), value: '' },
  ...(datos.value?.tipos || []).map((t) => ({
    label: t.label,
    value: t.value,
  })),
])
const opcionesClase = [
  { label: __('Todas'), value: '' },
  { label: __('Apertura'), value: 'Apertura' },
  { label: __('Diario'), value: 'Diario' },
  { label: __('Regularización'), value: 'Regularización' },
]

function parametros(extra = {}) {
  return {
    company: company.value,
    from_date: fromDate.value,
    to_date: toDate.value,
    page: pagina.value,
    page_size: tamano.value,
    search: busqueda.value || undefined,
    voucher_type: tipo.value || undefined,
    clase: clase.value || undefined,
    account: cuenta.value || undefined,
    ...extra,
  }
}

function load() {
  report.update({ params: parametros() })
  report.reload()
}

whenReady(load)
watch([busqueda, tipo, clase, cuenta, tamano], () => {
  if (pagina.value !== 1) pagina.value = 1
  else if (company.value) load()
})
watch(pagina, () => company.value && load())
watch(company, (_nueva, anterior) => {
  if (anterior) cuenta.value = ''
})

const subtitulo = computed(() =>
  etiquetaRango(
    datos.value?.from_date || fromDate.value,
    datos.value?.to_date || toDate.value,
  ),
)
const insignias = computed(() =>
  datos.value
    ? [
        { label: __('Ejercicio {0}', datos.value.fiscal_year), theme: 'blue' },
        { label: __('Código de Comercio, art. 28') },
      ]
    : [],
)

function abrirMayor(account) {
  router.push({
    name: 'GeneralLedger',
    query: {
      company: company.value,
      from: datos.value.from_date,
      to: datos.value.to_date,
      account,
    },
  })
}

async function exportar() {
  const todo = await call(
    'spain_compliance.api.informes.libro_diario',
    parametros({ page: 1, page_size: 0 }),
  )
  const filas = []
  for (const asiento of todo.entries) {
    for (const linea of asiento.lines) {
      filas.push([
        asiento.numero,
        formatDate(asiento.posting_date),
        asiento.voucher_label,
        asiento.voucher_no,
        linea.account_number,
        linea.account_name,
        linea.concepto,
        linea.tercero,
        linea.debit,
        linea.credit,
      ])
    }
  }
  descargarCsv(
    `libro-diario-${company.value}-${todo.from_date}-${todo.to_date}`,
    [
      __('Asiento'),
      __('Fecha'),
      __('Tipo'),
      __('Documento'),
      __('Cuenta'),
      __('Descripción'),
      __('Concepto'),
      __('Tercero'),
      __('Debe'),
      __('Haber'),
    ],
    filas,
  )
  if (todo.pagination.pages > 1) {
    toast.warning(
      __(
        'Se han exportado los primeros {0} asientos.',
        formatNumber(todo.entries.length, 0),
      ),
    )
  }
}
</script>
