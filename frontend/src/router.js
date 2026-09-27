import { createRouter, createWebHistory } from 'vue-router'
import { sessionStore } from '@/stores/session'

function placeholder(title, description, icon = 'box') {
  return {
    component: () => import('@/pages/PlaceholderPage.vue'),
    props: { title, description, icon },
  }
}

function docList(props) {
  return {
    component: () => import('@/pages/DocList.vue'),
    props,
  }
}

const routes = [
  {
    path: '/',
    redirect: { name: 'Dashboard' },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },

  // Ventas (Books)
  {
    path: '/sales-quotes',
    name: 'SalesQuotes',
    ...docList({
      title: 'Presupuestos',
      doctype: 'Quotation',
      deskPath: 'quotation',
      newLabel: 'Nuevo presupuesto',
      fields: [
        'name',
        'party_name',
        'transaction_date',
        'valid_till',
        'grand_total',
        'status',
      ],
      orderBy: 'transaction_date desc',
      columns: [
        { label: 'Presupuesto', key: 'name', width: '11rem' },
        { label: 'Cliente', key: 'party_name' },
        { label: 'Fecha', key: 'transaction_date', width: '9rem' },
        { label: 'Válido hasta', key: 'valid_till', width: '9rem' },
        { label: 'Total', key: 'grand_total', width: '9rem', align: 'end' },
        { label: 'Estado', key: 'status', width: '8rem' },
      ],
      emptyTitle: 'Sin presupuestos',
      emptyDescription: 'Todavía no hay presupuestos de venta en ERPNext',
    }),
  },
  {
    path: '/sales-invoices',
    name: 'SalesInvoices',
    ...docList({
      title: 'Facturas de venta',
      doctype: 'Sales Invoice',
      deskPath: 'sales-invoice',
      newLabel: 'Nueva factura',
      fields: [
        'name',
        'customer_name',
        'posting_date',
        'grand_total',
        'outstanding_amount',
        'status',
        'docstatus',
      ],
      orderBy: 'posting_date desc',
      columns: [
        { label: 'Factura', key: 'name', width: '11rem' },
        { label: 'Cliente', key: 'customer_name' },
        { label: 'Fecha', key: 'posting_date', width: '9rem' },
        { label: 'Total', key: 'grand_total', width: '9rem', align: 'end' },
        {
          label: 'Pendiente',
          key: 'outstanding_amount',
          width: '9rem',
          align: 'end',
        },
        { label: 'Estado', key: 'status', width: '8rem' },
      ],
      emptyTitle: 'Sin facturas de venta',
      emptyDescription: 'Todavía no hay facturas de venta en ERPNext',
    }),
  },
  {
    path: '/sales-payments',
    name: 'SalesPayments',
    ...docList({
      title: 'Cobros',
      doctype: 'Payment Entry',
      deskPath: 'payment-entry',
      newLabel: 'Nuevo cobro',
      filters: { payment_type: 'Receive' },
      fields: [
        'name',
        'party_name',
        'posting_date',
        'paid_amount',
        'mode_of_payment',
        'docstatus',
      ],
      orderBy: 'posting_date desc',
      columns: [
        { label: 'Cobro', key: 'name', width: '11rem' },
        { label: 'Cliente', key: 'party_name' },
        { label: 'Fecha', key: 'posting_date', width: '9rem' },
        { label: 'Importe', key: 'paid_amount', width: '9rem', align: 'end' },
        { label: 'Modo', key: 'mode_of_payment', width: '9rem' },
        { label: 'Estado', key: 'docstatus', width: '8rem' },
      ],
      emptyTitle: 'Sin cobros',
      emptyDescription: 'Todavía no hay cobros registrados en ERPNext',
    }),
  },
  {
    path: '/customers',
    name: 'Customers',
    ...docList({
      title: 'Clientes',
      doctype: 'Customer',
      deskPath: 'customer',
      newLabel: 'Nuevo cliente',
      fields: ['name', 'customer_name', 'customer_type', 'territory', 'disabled'],
      orderBy: 'modified desc',
      columns: [
        { label: 'ID', key: 'name', width: '11rem' },
        { label: 'Nombre', key: 'customer_name' },
        { label: 'Tipo', key: 'customer_type', width: '9rem' },
        { label: 'Territorio', key: 'territory', width: '10rem' },
      ],
      emptyTitle: 'Sin clientes',
      emptyDescription: 'Todavía no hay clientes en ERPNext',
    }),
  },
  {
    path: '/sales-items',
    name: 'SalesItems',
    ...docList({
      title: 'Artículos de venta',
      doctype: 'Item',
      deskPath: 'item',
      newLabel: 'Nuevo artículo',
      filters: { is_sales_item: 1 },
      fields: [
        'name',
        'item_name',
        'item_group',
        'stock_uom',
        'disabled',
      ],
      orderBy: 'modified desc',
      columns: [
        { label: 'Código', key: 'name', width: '11rem' },
        { label: 'Nombre', key: 'item_name' },
        { label: 'Grupo', key: 'item_group', width: '10rem' },
        { label: 'UdM', key: 'stock_uom', width: '6rem' },
      ],
      emptyTitle: 'Sin artículos de venta',
      emptyDescription: 'No hay artículos marcados como de venta',
    }),
  },

  // Compras (Books)
  {
    path: '/purchase-invoices',
    name: 'PurchaseInvoices',
    ...docList({
      title: 'Facturas de compra',
      doctype: 'Purchase Invoice',
      deskPath: 'purchase-invoice',
      newLabel: 'Nueva factura',
      fields: [
        'name',
        'supplier_name',
        'posting_date',
        'grand_total',
        'outstanding_amount',
        'status',
        'docstatus',
      ],
      orderBy: 'posting_date desc',
      columns: [
        { label: 'Factura', key: 'name', width: '11rem' },
        { label: 'Proveedor', key: 'supplier_name' },
        { label: 'Fecha', key: 'posting_date', width: '9rem' },
        { label: 'Total', key: 'grand_total', width: '9rem', align: 'end' },
        {
          label: 'Pendiente',
          key: 'outstanding_amount',
          width: '9rem',
          align: 'end',
        },
        { label: 'Estado', key: 'status', width: '8rem' },
      ],
      emptyTitle: 'Sin facturas de compra',
      emptyDescription: 'Todavía no hay facturas de compra en ERPNext',
    }),
  },
  {
    path: '/purchase-payments',
    name: 'PurchasePayments',
    ...docList({
      title: 'Pagos',
      doctype: 'Payment Entry',
      deskPath: 'payment-entry',
      newLabel: 'Nuevo pago',
      filters: { payment_type: 'Pay' },
      fields: [
        'name',
        'party_name',
        'posting_date',
        'paid_amount',
        'mode_of_payment',
        'docstatus',
      ],
      orderBy: 'posting_date desc',
      columns: [
        { label: 'Pago', key: 'name', width: '11rem' },
        { label: 'Proveedor', key: 'party_name' },
        { label: 'Fecha', key: 'posting_date', width: '9rem' },
        { label: 'Importe', key: 'paid_amount', width: '9rem', align: 'end' },
        { label: 'Modo', key: 'mode_of_payment', width: '9rem' },
        { label: 'Estado', key: 'docstatus', width: '8rem' },
      ],
      emptyTitle: 'Sin pagos',
      emptyDescription: 'Todavía no hay pagos registrados en ERPNext',
    }),
  },
  {
    path: '/suppliers',
    name: 'Suppliers',
    ...docList({
      title: 'Proveedores',
      doctype: 'Supplier',
      deskPath: 'supplier',
      newLabel: 'Nuevo proveedor',
      fields: [
        'name',
        'supplier_name',
        'supplier_group',
        'country',
        'disabled',
      ],
      orderBy: 'modified desc',
      columns: [
        { label: 'ID', key: 'name', width: '11rem' },
        { label: 'Nombre', key: 'supplier_name' },
        { label: 'Grupo', key: 'supplier_group', width: '10rem' },
        { label: 'País', key: 'country', width: '9rem' },
      ],
      emptyTitle: 'Sin proveedores',
      emptyDescription: 'Todavía no hay proveedores en ERPNext',
    }),
  },
  {
    path: '/purchase-items',
    name: 'PurchaseItems',
    ...docList({
      title: 'Artículos de compra',
      doctype: 'Item',
      deskPath: 'item',
      newLabel: 'Nuevo artículo',
      filters: { is_purchase_item: 1 },
      fields: [
        'name',
        'item_name',
        'item_group',
        'stock_uom',
        'disabled',
      ],
      orderBy: 'modified desc',
      columns: [
        { label: 'Código', key: 'name', width: '11rem' },
        { label: 'Nombre', key: 'item_name' },
        { label: 'Grupo', key: 'item_group', width: '10rem' },
        { label: 'UdM', key: 'stock_uom', width: '6rem' },
      ],
      emptyTitle: 'Sin artículos de compra',
      emptyDescription: 'No hay artículos marcados como de compra',
    }),
  },

  // Común (Books)
  {
    path: '/journal-entries',
    name: 'JournalEntries',
    component: () => import('@/pages/JournalEntries.vue'),
  },
  {
    path: '/parties',
    name: 'Parties',
    ...placeholder(
      'Terceros',
      'Vista unificada de clientes y proveedores (como Party en Frappe Books). Por ahora usa Clientes y Proveedores.',
      'contact',
    ),
  },
  {
    path: '/items',
    name: 'Items',
    ...docList({
      title: 'Artículos',
      doctype: 'Item',
      deskPath: 'item',
      newLabel: 'Nuevo artículo',
      fields: [
        'name',
        'item_name',
        'item_group',
        'stock_uom',
        'is_sales_item',
        'is_purchase_item',
        'disabled',
      ],
      orderBy: 'modified desc',
      columns: [
        { label: 'Código', key: 'name', width: '11rem' },
        { label: 'Nombre', key: 'item_name' },
        { label: 'Grupo', key: 'item_group', width: '10rem' },
        { label: 'UdM', key: 'stock_uom', width: '6rem' },
      ],
      emptyTitle: 'Sin artículos',
      emptyDescription: 'Todavía no hay artículos en ERPNext',
    }),
  },
  {
    path: '/price-lists',
    name: 'PriceLists',
    ...docList({
      title: 'Listas de precios',
      doctype: 'Price List',
      deskPath: 'price-list',
      newLabel: 'Nueva lista',
      fields: ['name', 'currency', 'buying', 'selling', 'enabled'],
      orderBy: 'modified desc',
      columns: [
        { label: 'Lista', key: 'name' },
        { label: 'Moneda', key: 'currency', width: '8rem' },
        { label: 'Compra', key: 'buying', width: '6rem' },
        { label: 'Venta', key: 'selling', width: '6rem' },
        { label: 'Activa', key: 'enabled', width: '6rem' },
      ],
      emptyTitle: 'Sin listas de precios',
      emptyDescription: 'Todavía no hay listas de precios en ERPNext',
    }),
  },

  // Informes (Books)
  {
    path: '/general-ledger',
    name: 'GeneralLedger',
    ...placeholder(
      'Libro mayor',
      'Consulta de movimientos por cuenta y periodo (informe ERPNext General Ledger).',
      'layers',
    ),
  },
  {
    path: '/profit-and-loss',
    name: 'ProfitAndLoss',
    ...placeholder(
      'Pérdidas y ganancias',
      'Cuenta de resultados: ingresos, costes y beneficio del periodo.',
      'trending-up',
    ),
  },
  {
    path: '/balance-sheet',
    name: 'BalanceSheet',
    ...placeholder(
      'Balance de situación',
      'Activo, pasivo y patrimonio neto a una fecha determinada.',
      'scale',
    ),
  },
  {
    path: '/trial-balance',
    name: 'TrialBalance',
    ...placeholder(
      'Sumas y saldos',
      'Comprobación de cuadre de débitos y créditos por cuenta.',
      'sigma',
    ),
  },

  // Cumplimiento (España)
  {
    path: '/sii',
    name: 'SII',
    ...placeholder(
      'SII',
      'Suministro Inmediato de Información a la AEAT (facturas emitidas y recibidas).',
      'send',
    ),
  },
  {
    path: '/verifactu',
    name: 'Verifactu',
    ...placeholder(
      'Verifactu',
      'Sistema de verificación de facturas y huellas de registro.',
      'shield-check',
    ),
  },
  {
    path: '/tax-returns',
    name: 'TaxReturns',
    ...placeholder(
      'Modelos de Hacienda',
      'Modelos 303, 390, 347, 111, 190 y resto de declaraciones.',
      'clipboard-list',
    ),
  },

  // Configuración (Books Setup)
  {
    path: '/chart-of-accounts',
    name: 'ChartOfAccounts',
    ...placeholder(
      'Plan de cuentas',
      'Árbol del Plan General Contable español y cuentas de la compañía.',
      'book-open',
    ),
  },
  {
    path: '/tax-templates',
    name: 'TaxTemplates',
    ...docList({
      title: 'Plantillas de impuestos',
      doctype: 'Sales Taxes and Charges Template',
      deskPath: 'sales-taxes-and-charges-template',
      newLabel: 'Nueva plantilla',
      fields: ['name', 'title', 'company', 'is_default', 'disabled'],
      orderBy: 'modified desc',
      columns: [
        { label: 'Plantilla', key: 'name' },
        { label: 'Título', key: 'title', width: '12rem' },
        { label: 'Compañía', key: 'company', width: '12rem' },
        { label: 'Por defecto', key: 'is_default', width: '7rem' },
      ],
      emptyTitle: 'Sin plantillas de impuestos',
      emptyDescription: 'Todavía no hay plantillas de impuestos de venta',
    }),
  },
  {
    path: '/settings',
    name: 'Settings',
    ...placeholder(
      'Ajustes',
      'Parámetros fiscales, certificados AEAT y opciones de la compañía.',
      'settings',
    ),
  },

  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    ...placeholder(
      'Página no encontrada',
      'La ruta solicitada no existe en Contabilidad.',
      'circle-alert',
    ),
  },
]

const router = createRouter({
  history: createWebHistory('/contabilidad'),
  routes,
})

router.beforeEach((to, from, next) => {
  const session = sessionStore()
  if (!session.isLoggedIn) {
    window.location.href = `/login?redirect-to=/contabilidad${to.fullPath}`
    return
  }
  next()
})

export default router
