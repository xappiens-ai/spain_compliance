<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs
        :items="[{ label: __('Tablero contable'), route: { name: 'Dashboard' } }]"
      />
    </template>
    <template #right-header>
      <div class="flex items-center gap-2">
        <TabButtons v-model="period" :options="periodButtons" size="sm" />
        <Button
          :label="__('Actualizar')"
          variant="subtle"
          :loading="tablero.loading"
          @click="tablero.reload()"
        >
          <template #prefix>
            <LucideRefreshCcw class="size-4" />
          </template>
        </Button>
      </div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-5 overflow-auto p-4 sm:p-5">
    <div
      v-if="tablero.loading && !tablero.data"
      class="flex flex-1 items-center justify-center"
    >
      <LoadingIndicator :scale="8" />
    </div>

    <template v-else-if="tablero.data">
      <div class="flex flex-col gap-1">
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __('Tablero contable') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          <span v-if="tablero.data.company">{{ tablero.data.company }} · </span>
          {{ tablero.data.period_label }}
          ({{ formatDate(tablero.data.from_date) }} –
          {{ formatDate(tablero.data.to_date) }})
        </p>
      </div>

      <!-- KPI strip -->
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <button
          v-for="kpi in kpis"
          :key="kpi.key"
          type="button"
          class="flex flex-col gap-2 rounded-lg border border-outline-gray-1 bg-surface-white p-4 text-left transition hover:bg-surface-gray-1"
          @click="kpi.route && $router.push({ name: kpi.route })"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-p-sm text-ink-gray-6">{{ __(kpi.label) }}</span>
            <component
              :is="kpi.icon"
              class="size-4 shrink-0 text-ink-gray-5"
            />
          </div>
          <div class="text-xl font-semibold tabular-nums text-ink-gray-9">
            {{ kpi.value }}
          </div>
          <div class="text-p-sm text-ink-gray-5">{{ kpi.hint }}</div>
        </button>
      </div>

      <!-- Charts (Books-style cashflow + mix) -->
      <div class="grid gap-3 xl:grid-cols-3">
        <section
          class="xl:col-span-2 flex min-h-[320px] flex-col rounded-lg border border-outline-gray-1 bg-surface-white p-2 sm:p-4"
        >
          <AxisChart
            v-if="cashflowConfig.data?.length"
            class="min-h-[280px] w-full flex-1"
            :config="cashflowConfig"
          />
          <div
            v-else
            class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
          >
            {{ __('Sin datos de flujo para el periodo') }}
          </div>
        </section>
        <section
          class="flex min-h-[320px] flex-col rounded-lg border border-outline-gray-1 bg-surface-white p-2 sm:p-4"
        >
          <DonutChart
            v-if="receivableMixConfig.data?.length"
            class="min-h-[280px] w-full flex-1"
            :config="receivableMixConfig"
          />
        </section>
      </div>

      <section
        class="flex min-h-[320px] flex-col rounded-lg border border-outline-gray-1 bg-surface-white p-2 sm:p-4"
      >
        <AxisChart
          v-if="billingConfig.data?.length"
          class="min-h-[280px] w-full flex-1"
          :config="billingConfig"
        />
        <div
          v-else
          class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
        >
          {{ __('Sin datos de facturación para el periodo') }}
        </div>
      </section>

      <!-- Unpaid widgets (Books-style) -->
      <div class="grid gap-3 lg:grid-cols-2">
        <section
          class="flex flex-col gap-4 rounded-lg border border-outline-gray-1 bg-surface-white p-4"
        >
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-base font-medium text-ink-gray-9">
              {{ __('Facturas de venta') }}
            </h3>
            <Button
              :label="__('Ver listado')"
              variant="ghost"
              @click="$router.push({ name: 'SalesInvoices' })"
            />
          </div>
          <InvoiceProgress
            :paid="data.receivable.paid"
            :unpaid="data.receivable.outstanding"
            :currency="data.currency"
            paid-label="Cobrado (periodo)"
            unpaid-label="Pendiente de cobro"
            bar-theme="green"
          />
          <RecentInvoices
            :rows="data.recent_sales"
            party-key="customer_name"
            :currency="data.currency"
            empty-label="Sin facturas de venta recientes"
            @open="openDesk('sales-invoice', $event)"
          />
        </section>

        <section
          class="flex flex-col gap-4 rounded-lg border border-outline-gray-1 bg-surface-white p-4"
        >
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-base font-medium text-ink-gray-9">
              {{ __('Facturas de compra') }}
            </h3>
            <Button
              :label="__('Ver listado')"
              variant="ghost"
              @click="$router.push({ name: 'PurchaseInvoices' })"
            />
          </div>
          <InvoiceProgress
            :paid="data.payable.paid"
            :unpaid="data.payable.outstanding"
            :currency="data.currency"
            paid-label="Pagado (periodo)"
            unpaid-label="Pendiente de pago"
            bar-theme="orange"
          />
          <RecentInvoices
            :rows="data.recent_purchases"
            party-key="supplier_name"
            :currency="data.currency"
            empty-label="Sin facturas de compra recientes"
            @open="openDesk('purchase-invoice', $event)"
          />
        </section>
      </div>

      <!-- Shortcuts -->
      <section
        class="rounded-lg border border-outline-gray-1 bg-surface-white p-4"
      >
        <h3 class="mb-3 text-base font-medium text-ink-gray-9">
          {{ __('Accesos rápidos') }}
        </h3>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="link in shortcuts"
            :key="link.name"
            :label="__(link.label)"
            variant="subtle"
            @click="$router.push({ name: link.name })"
          >
            <template #prefix>
              <component :is="link.icon" class="size-4" />
            </template>
          </Button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, markRaw, ref, watch } from 'vue'
import {
  AxisChart,
  Breadcrumbs,
  Button,
  DonutChart,
  LoadingIndicator,
  TabButtons,
  createResource,
  dayjs,
} from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import InvoiceProgress from '@/components/dashboard/InvoiceProgress.vue'
import RecentInvoices from '@/components/dashboard/RecentInvoices.vue'

import LucideRefreshCcw from '~icons/lucide/refresh-ccw'
import LucideBanknote from '~icons/lucide/banknote'
import LucideReceipt from '~icons/lucide/receipt'
import LucideShoppingCart from '~icons/lucide/shopping-cart'
import LucideBookOpen from '~icons/lucide/book-open'
import LucideLayers from '~icons/lucide/layers'
import LucideTrendingUp from '~icons/lucide/trending-up'
import LucideSend from '~icons/lucide/send'

const period = ref('this_year')

const periodButtons = [
  { label: __('Este mes'), value: 'this_month' },
  { label: __('Trimestre'), value: 'this_quarter' },
  { label: __('Este año'), value: 'this_year' },
]

const tablero = createResource({
  url: 'spain_compliance.api.dashboard.get_tablero',
  params: { period: period.value },
  auto: true,
})

watch(period, (value) => {
  tablero.update({ params: { period: value } })
  tablero.reload()
})

const data = computed(() => tablero.data || {
  receivable: { paid: 0, outstanding: 0, billed: 0, count: 0, period_count: 0 },
  payable: { paid: 0, outstanding: 0, billed: 0, count: 0, period_count: 0 },
  journal_entries: { count: 0, draft: 0 },
  currency: 'EUR',
  chart_grain: 'month',
  cashflow: [],
  billing: [],
  receivable_mix: [],
  recent_sales: [],
  recent_purchases: [],
})

const cashflowConfig = computed(() => ({
  data: data.value.cashflow || [],
  title: __('Flujo de caja'),
  subtitle: __('Entradas y salidas del periodo'),
  colors: ['#059669', '#F43F5E'],
  xAxis: {
    key: 'date',
    type: 'time',
    timeGrain: data.value.chart_grain === 'day' ? 'day' : 'month',
    title: __('Fecha'),
  },
  yAxis: {
    title: data.value.currency || 'EUR',
  },
  series: [
    {
      name: 'entradas',
      type: 'area',
      color: '#059669',
      showDataPoints: true,
      fillOpacity: 0.25,
    },
    {
      name: 'salidas',
      type: 'area',
      color: '#F43F5E',
      showDataPoints: true,
      fillOpacity: 0.2,
    },
  ],
}))

const billingConfig = computed(() => ({
  data: data.value.billing || [],
  title: __('Facturación'),
  subtitle: __('Ventas frente a compras'),
  colors: ['#2490EF', '#F59E0B'],
  xAxis: {
    key: 'date',
    type: 'time',
    timeGrain: data.value.chart_grain === 'day' ? 'day' : 'month',
    title: __('Fecha'),
  },
  yAxis: {
    title: data.value.currency || 'EUR',
  },
  series: [
    {
      name: 'ventas',
      type: 'bar',
      color: '#2490EF',
    },
    {
      name: 'compras',
      type: 'bar',
      color: '#F59E0B',
    },
  ],
}))

const receivableMixConfig = computed(() => ({
  data: data.value.receivable_mix || [],
  title: __('Cobros'),
  subtitle: __('Cobrado vs pendiente'),
  colors: ['#059669', '#F59E0B'],
  categoryColumn: 'label',
  valueColumn: 'value',
  maxSliceCount: 4,
}))

const currencyFormatters = {}

function money(amount, currency = 'EUR') {
  if (!currencyFormatters[currency]) {
    currencyFormatters[currency] = new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    })
  }
  return currencyFormatters[currency].format(Number(amount) || 0)
}

function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}

const kpis = computed(() => {
  const d = data.value
  const cur = d.currency || 'EUR'
  return [
    {
      key: 'receivable',
      label: 'Cobros pendientes',
      value: money(d.receivable.outstanding, cur),
      hint: __('{0} facturas abiertas', d.receivable.count || 0),
      icon: markRaw(LucideBanknote),
      route: 'SalesInvoices',
    },
    {
      key: 'payable',
      label: 'Pagos pendientes',
      value: money(d.payable.outstanding, cur),
      hint: __('{0} facturas abiertas', d.payable.count || 0),
      icon: markRaw(LucideShoppingCart),
      route: 'PurchaseInvoices',
    },
    {
      key: 'billed',
      label: 'Facturado (periodo)',
      value: money(d.receivable.billed, cur),
      hint: __('{0} facturas de venta', d.receivable.period_count || 0),
      icon: markRaw(LucideReceipt),
      route: 'SalesInvoices',
    },
    {
      key: 'journals',
      label: 'Asientos (periodo)',
      value: String(d.journal_entries.count || 0),
      hint: __('{0} en borrador', d.journal_entries.draft || 0),
      icon: markRaw(LucideBookOpen),
      route: 'JournalEntries',
    },
  ]
})

const shortcuts = [
  {
    name: 'JournalEntries',
    label: 'Asientos',
    icon: markRaw(LucideBookOpen),
  },
  {
    name: 'GeneralLedger',
    label: 'Libro mayor',
    icon: markRaw(LucideLayers),
  },
  {
    name: 'ProfitAndLoss',
    label: 'Pérdidas y ganancias',
    icon: markRaw(LucideTrendingUp),
  },
  {
    name: 'SII',
    label: 'SII',
    icon: markRaw(LucideSend),
  },
]

function openDesk(deskPath, name) {
  window.open(`/app/${deskPath}/${name}`, '_blank')
}
</script>
