import { markRaw } from 'vue'

import LucideLayoutDashboard from '~icons/lucide/layout-dashboard'
import LucideFileText from '~icons/lucide/file-text'
import LucideReceipt from '~icons/lucide/receipt'
import LucideBanknote from '~icons/lucide/banknote'
import LucideUsers from '~icons/lucide/users'
import LucidePackage from '~icons/lucide/package'
import LucideShoppingCart from '~icons/lucide/shopping-cart'
import LucideTruck from '~icons/lucide/truck'
import LucideBookOpen from '~icons/lucide/book-open'
import LucideLayers from '~icons/lucide/layers'
import LucideTrendingUp from '~icons/lucide/trending-up'
import LucideScale from '~icons/lucide/scale'
import LucideSigma from '~icons/lucide/sigma'
import LucideTags from '~icons/lucide/tags'
import LucidePercent from '~icons/lucide/percent'
import LucideSend from '~icons/lucide/send'
import LucideShieldCheck from '~icons/lucide/shield-check'
import LucideClipboardList from '~icons/lucide/clipboard-list'
import LucideSettings from '~icons/lucide/settings'
import LucideContact from '~icons/lucide/contact'

/**
 * Sidebar inspired by Frappe Books (src/utils/sidebarConfig.ts),
 * plus Spanish compliance sections. Labels in Spanish for Contabilidad.
 */
export const navigation = [
  {
    label: null,
    items: [
      {
        name: 'Dashboard',
        label: 'Tablero',
        icon: markRaw(LucideLayoutDashboard),
      },
    ],
  },
  {
    label: 'Ventas',
    collapsible: true,
    items: [
      {
        name: 'SalesQuotes',
        label: 'Presupuestos',
        icon: markRaw(LucideFileText),
      },
      {
        name: 'SalesInvoices',
        label: 'Facturas de venta',
        icon: markRaw(LucideReceipt),
      },
      {
        name: 'SalesPayments',
        label: 'Cobros',
        icon: markRaw(LucideBanknote),
      },
      {
        name: 'Customers',
        label: 'Clientes',
        icon: markRaw(LucideUsers),
      },
      {
        name: 'SalesItems',
        label: 'Artículos de venta',
        icon: markRaw(LucidePackage),
      },
    ],
  },
  {
    label: 'Compras',
    collapsible: true,
    items: [
      {
        name: 'PurchaseInvoices',
        label: 'Facturas de compra',
        icon: markRaw(LucideShoppingCart),
      },
      {
        name: 'PurchasePayments',
        label: 'Pagos',
        icon: markRaw(LucideBanknote),
      },
      {
        name: 'Suppliers',
        label: 'Proveedores',
        icon: markRaw(LucideTruck),
      },
      {
        name: 'PurchaseItems',
        label: 'Artículos de compra',
        icon: markRaw(LucidePackage),
      },
    ],
  },
  {
    label: 'Común',
    collapsible: true,
    items: [
      {
        name: 'JournalEntries',
        label: 'Asientos',
        icon: markRaw(LucideBookOpen),
      },
      {
        name: 'Parties',
        label: 'Terceros',
        icon: markRaw(LucideContact),
      },
      {
        name: 'Items',
        label: 'Artículos',
        icon: markRaw(LucidePackage),
      },
      {
        name: 'PriceLists',
        label: 'Listas de precios',
        icon: markRaw(LucideTags),
      },
    ],
  },
  {
    label: 'Informes',
    collapsible: true,
    items: [
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
        name: 'BalanceSheet',
        label: 'Balance de situación',
        icon: markRaw(LucideScale),
      },
      {
        name: 'TrialBalance',
        label: 'Sumas y saldos',
        icon: markRaw(LucideSigma),
      },
    ],
  },
  {
    label: 'Cumplimiento',
    collapsible: true,
    items: [
      { name: 'SII', label: 'SII', icon: markRaw(LucideSend) },
      {
        name: 'Verifactu',
        label: 'Verifactu',
        icon: markRaw(LucideShieldCheck),
      },
      {
        name: 'TaxReturns',
        label: 'Modelos Hacienda',
        icon: markRaw(LucideClipboardList),
      },
    ],
  },
  {
    label: 'Configuración',
    collapsible: true,
    items: [
      {
        name: 'ChartOfAccounts',
        label: 'Plan de cuentas',
        icon: markRaw(LucideBookOpen),
      },
      {
        name: 'TaxTemplates',
        label: 'Plantillas de impuestos',
        icon: markRaw(LucidePercent),
      },
      {
        name: 'Settings',
        label: 'Ajustes',
        icon: markRaw(LucideSettings),
      },
    ],
  },
]
