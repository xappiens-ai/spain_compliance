import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createResource, dayjs } from 'frappe-ui'

export function useInformePeriodo() {
  const route = useRoute()
  const company = ref('')
  const fromDate = ref('')
  const toDate = ref('')
  const companies = ref([])
  const today = ref(dayjs().format('YYYY-MM-DD'))
  const ready = ref(false)

  const contexto = createResource({
    url: 'spain_compliance.api.informes.get_contexto',
    auto: true,
    onSuccess(data) {
      companies.value = data?.companies || []
      today.value = data?.today || today.value
      const query = route?.query || {}
      const nombres = companies.value.map((row) => row.name)
      company.value =
        query.company && nombres.includes(query.company)
          ? query.company
          : data?.company || ''
      fromDate.value = query.from || data?.from_date || ''
      toDate.value = query.to || data?.to_date || ''
      ready.value = true
    },
  })

  const companyInfo = computed(
    () => companies.value.find((row) => row.name === company.value) || null,
  )
  const fiscalYears = computed(() => companyInfo.value?.fiscal_years || [])

  function whenReady(callback) {
    watch(
      [company, fromDate, toDate, ready],
      () => {
        if (ready.value && company.value && fromDate.value && toDate.value) {
          callback()
        }
      },
      { immediate: true },
    )
  }

  return {
    company,
    fromDate,
    toDate,
    companies,
    companyInfo,
    fiscalYears,
    today,
    contexto,
    ready,
    whenReady,
  }
}

const formatters = {}

function formatter(key, options) {
  if (!formatters[key]) {
    try {
      formatters[key] = new Intl.NumberFormat('es-ES', options)
    } catch {
      formatters[key] = new Intl.NumberFormat('es-ES', {
        ...options,
        currency: 'EUR',
      })
    }
  }
  return formatters[key]
}

export function formatMoney(amount, currency = 'EUR') {
  return formatter(`money-${currency}`, {
    style: 'currency',
    currency: currency || 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount) || 0)
}

export function formatNumber(amount, decimals = 2) {
  return formatter(`num-${decimals}`, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(amount) || 0)
}

/** Importe en formato contable: sin símbolo, guion para el cero. */
export function formatImporte(amount) {
  const value = Number(amount) || 0
  if (Math.abs(value) < 0.005) return '—'
  return formatNumber(value, 2)
}

export function formatCompact(amount, currency = 'EUR') {
  const value = Number(amount) || 0
  const abs = Math.abs(value)
  const symbol = currency === 'EUR' ? '€' : currency
  if (abs >= 1e6)
    return `${formatNumber(value / 1e6, abs >= 1e8 ? 0 : 2)} M${symbol}`
  if (abs >= 1e4)
    return `${formatNumber(value / 1e3, abs >= 1e5 ? 0 : 1)} k${symbol}`
  return `${formatNumber(value, abs >= 100 ? 0 : 2)} ${symbol}`
}

export function formatPct(value, decimals = 1) {
  if (value === null || value === undefined || !Number.isFinite(value))
    return '—'
  return `${formatNumber(value * 100, decimals)} %`
}

export function formatRatio(value, decimals = 2) {
  if (value === null || value === undefined || !Number.isFinite(value))
    return '—'
  return formatNumber(value, decimals)
}

export function formatDate(value) {
  return value ? dayjs(value).format('DD/MM/YYYY') : ''
}

export function variacion(actual, anterior) {
  const a = Number(actual) || 0
  const b = Number(anterior) || 0
  return {
    abs: a - b,
    pct: Math.abs(b) >= 0.005 ? (a - b) / Math.abs(b) : null,
  }
}

export function errorMessage(error) {
  if (!error) return ''
  if (Array.isArray(error.messages) && error.messages.length) {
    return error.messages.map((item) => item.message || item).join(' ')
  }
  if (typeof error.exc_type === 'string' && error._server_messages) {
    try {
      const parsed = JSON.parse(error._server_messages).map((item) =>
        JSON.parse(item),
      )
      return parsed.map((item) => item.message).join(' ')
    } catch {
      return error.message || __('No se ha podido cargar el informe')
    }
  }
  return (
    error.message || error.exception || __('No se ha podido cargar el informe')
  )
}

export function openDesk(doctype, name) {
  if (!doctype || !name) return
  const slug = String(doctype).toLowerCase().replaceAll(' ', '-')
  window.open(`/app/${slug}/${encodeURIComponent(name)}`, '_blank')
}

function celdaCsv(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number')
    return formatNumber(value, 2).replaceAll('.', '')
  const text = String(value)
  return /[";\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

/** CSV con «;» y coma decimal, como lo abre Excel en español. */
export function descargarCsv(nombre, cabeceras, filas) {
  const lineas = [cabeceras, ...filas].map((fila) =>
    fila.map(celdaCsv).join(';'),
  )
  const blob = new Blob([`\ufeff${lineas.join('\r\n')}`], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = `${nombre}.csv`
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function rango(key, label, from, to) {
  return {
    key,
    label,
    from: from.format('YYYY-MM-DD'),
    to: to.format('YYYY-MM-DD'),
  }
}

/** Periodos rápidos a partir de los ejercicios de la compañía. */
export function periodosRapidos(fiscalYears, today) {
  const hoy = dayjs(today)
  const presets = []
  const actual = fiscalYears.find(
    (fy) => !hoy.isBefore(dayjs(fy.start)) && !hoy.isAfter(dayjs(fy.end)),
  )
  if (actual) {
    presets.push(
      rango(
        'fy',
        __('Ejercicio {0} hasta hoy', actual.name),
        dayjs(actual.start),
        hoy,
      ),
    )
    presets.push(
      rango(
        'fy-full',
        __('Ejercicio {0} completo', actual.name),
        dayjs(actual.start),
        dayjs(actual.end),
      ),
    )
  }
  const mes = hoy.startOf('month')
  presets.push(rango('month', __('Este mes'), mes, hoy))
  presets.push(
    rango(
      'prev-month',
      __('Mes anterior'),
      mes.subtract(1, 'month'),
      mes.subtract(1, 'day'),
    ),
  )
  const trimestre = hoy.month() - (hoy.month() % 3)
  const inicioTrimestre = hoy.month(trimestre).startOf('month')
  presets.push(rango('quarter', __('Este trimestre'), inicioTrimestre, hoy))
  presets.push(
    rango(
      'prev-quarter',
      __('Trimestre anterior'),
      inicioTrimestre.subtract(3, 'month'),
      inicioTrimestre.subtract(1, 'day'),
    ),
  )
  for (const fy of fiscalYears) {
    if (actual && fy.name === actual.name) continue
    if (dayjs(fy.start).isAfter(hoy)) continue
    presets.push(
      rango(
        `fy-${fy.name}`,
        __('Ejercicio {0}', fy.name),
        dayjs(fy.start),
        dayjs(fy.end),
      ),
    )
    if (presets.length > 9) break
  }
  return presets
}

/** Fechas de cierre rápidas para informes «a fecha». */
export function fechasRapidas(fiscalYears, today) {
  const hoy = dayjs(today)
  const presets = [
    { key: 'today', label: __('Hoy'), to: hoy.format('YYYY-MM-DD') },
  ]
  presets.push({
    key: 'month-end',
    label: __('Fin del mes anterior'),
    to: hoy.startOf('month').subtract(1, 'day').format('YYYY-MM-DD'),
  })
  const trimestre = hoy.month() - (hoy.month() % 3)
  presets.push({
    key: 'quarter-end',
    label: __('Fin del trimestre anterior'),
    to: hoy
      .month(trimestre)
      .startOf('month')
      .subtract(1, 'day')
      .format('YYYY-MM-DD'),
  })
  for (const fy of fiscalYears) {
    if (!dayjs(fy.end).isBefore(hoy)) continue
    presets.push({
      key: `fy-${fy.name}`,
      label: __('Cierre {0}', fy.name),
      to: fy.end,
    })
    if (presets.length > 7) break
  }
  return presets
}

export function etiquetaRango(from, to) {
  if (!from || !to) return ''
  const a = dayjs(from)
  const b = dayjs(to)
  if (a.year() === b.year())
    return `${a.format('DD/MM')} – ${b.format('DD/MM/YYYY')}`
  return `${a.format('DD/MM/YYYY')} – ${b.format('DD/MM/YYYY')}`
}
