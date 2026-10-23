import { ref, watch } from 'vue'
import { createResource } from 'frappe-ui'

export function useInformePeriodo() {
  const company = ref('')
  const fromDate = ref('')
  const toDate = ref('')
  const companies = ref([])
  const ready = ref(false)

  const contexto = createResource({
    url: 'spain_compliance.api.informes.get_contexto',
    auto: true,
    onSuccess(data) {
      companies.value = data?.companies || []
      company.value = data?.company || ''
      fromDate.value = data?.from_date || ''
      toDate.value = data?.to_date || ''
      ready.value = true
    },
  })

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

  return { company, fromDate, toDate, companies, contexto, ready, whenReady }
}

export function formatMoney(amount, currency = 'EUR') {
  try {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency || 'EUR',
      maximumFractionDigits: 2,
    }).format(Number(amount) || 0)
  } catch {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 2,
    }).format(Number(amount) || 0)
  }
}

export function errorMessage(error) {
  if (!error) return ''
  if (Array.isArray(error.messages) && error.messages.length) {
    return error.messages.map((item) => item.message || item).join(' ')
  }
  if (typeof error.exc_type === 'string' && error._server_messages) {
    try {
      const parsed = JSON.parse(error._server_messages).map((item) => JSON.parse(item))
      return parsed.map((item) => item.message).join(' ')
    } catch {
      return error.message || __('No se ha podido cargar el informe')
    }
  }
  return error.message || error.exception || __('No se ha podido cargar el informe')
}

export function openDesk(doctype, name) {
  if (!doctype || !name) return
  const slug = String(doctype).toLowerCase().replaceAll(' ', '-')
  window.open(`/app/${slug}/${name}`, '_blank')
}
