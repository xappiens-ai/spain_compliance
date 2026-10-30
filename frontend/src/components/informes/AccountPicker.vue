<template>
  <Combobox
    v-model="seleccion"
    v-model:query="consulta"
    :options="opciones"
    :loading="cargando"
    :filterable="false"
    trigger="button"
    :placeholder="placeholder"
    :empty-text="__('Ninguna cuenta coincide')"
    class="w-80"
    @update:query="buscarConRetardo"
    @update:open="alAbrir"
  >
    <template #item-label="{ item }">
      <div class="flex min-w-0 items-center gap-2">
        <span
          v-if="item.numero"
          class="shrink-0 tabular-nums text-ink-gray-5"
          >{{ item.numero }}</span
        >
        <span class="truncate">{{ item.nombre }}</span>
        <Badge
          v-if="item.is_group"
          class="ml-auto shrink-0"
          :label="__('grupo')"
          size="sm"
        />
      </div>
    </template>
  </Combobox>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { Badge, Combobox, call } from 'frappe-ui'

const TODAS = '__todas__'

const modelo = defineModel({ type: String, default: '' })

const props = defineProps({
  company: { type: String, required: true },
  permitirTodas: { type: Boolean, default: true },
  placeholder: { type: String, default: () => __('Todas las cuentas') },
})

const consulta = ref('')
const resultados = ref([])
const conocidas = ref(new Map())
const cargando = ref(false)
let peticion = 0

function opcion(row) {
  return {
    label: row.numero ? `${row.numero} ${row.nombre}` : row.nombre,
    value: row.account,
    numero: row.numero,
    nombre: row.nombre,
    is_group: row.is_group,
  }
}

const seleccion = computed({
  get: () => modelo.value || (props.permitirTodas ? TODAS : null),
  set: (valor) => {
    modelo.value = !valor || valor === TODAS ? '' : valor
  },
})

const opciones = computed(() => {
  const lista = []
  if (props.permitirTodas && !consulta.value) {
    lista.push({
      label: __('Todas las cuentas'),
      value: TODAS,
      nombre: __('Todas las cuentas'),
    })
  }
  const vistos = new Set()
  for (const row of resultados.value) {
    vistos.add(row.account)
    lista.push(opcion(row))
  }
  if (
    modelo.value &&
    !vistos.has(modelo.value) &&
    conocidas.value.has(modelo.value)
  ) {
    lista.push(opcion(conocidas.value.get(modelo.value)))
  }
  return lista
})

async function buscar(texto) {
  if (!props.company) return
  const id = ++peticion
  cargando.value = true
  try {
    const filas = await call('spain_compliance.api.informes.buscar_cuentas', {
      company: props.company,
      txt: texto || '',
      limit: 40,
    })
    if (id !== peticion) return
    resultados.value = filas || []
    for (const row of resultados.value) conocidas.value.set(row.account, row)
  } finally {
    if (id === peticion) cargando.value = false
  }
}

const buscarConRetardo = useDebounceFn(buscar, 250)

function alAbrir(abierto) {
  if (abierto && !resultados.value.length) buscar(consulta.value)
}

async function resolverEtiqueta(account) {
  if (!account || conocidas.value.has(account)) return
  const numero = (account.match(/^\d+/) || [''])[0]
  const filas = await call('spain_compliance.api.informes.buscar_cuentas', {
    company: props.company,
    txt: numero || account,
    limit: 10,
  })
  for (const row of filas || []) conocidas.value.set(row.account, row)
}

watch(modelo, resolverEtiqueta, { immediate: true })
watch(
  () => props.company,
  () => {
    resultados.value = []
  },
)
</script>
