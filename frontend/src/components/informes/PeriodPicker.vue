<template>
  <div class="flex flex-wrap items-end gap-2">
    <CampoFiltro :label="asOf ? __('Fecha del balance') : __('Periodo')">
      <Select v-model="atajo" :options="opciones" class="w-56" />
    </CampoFiltro>
    <CampoFiltro v-if="!asOf" :label="__('Desde')">
      <TextInput v-model="desde" type="date" class="w-36" />
    </CampoFiltro>
    <CampoFiltro :label="asOf ? __('A fecha') : __('Hasta')">
      <TextInput v-model="hasta" type="date" class="w-36" />
    </CampoFiltro>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Select, TextInput } from 'frappe-ui'
import CampoFiltro from '@/components/informes/CampoFiltro.vue'
import { fechasRapidas, periodosRapidos } from '@/composables/informe'

const desde = defineModel('from', { type: String, default: '' })
const hasta = defineModel('to', { type: String, default: '' })

const props = defineProps({
  fiscalYears: { type: Array, default: () => [] },
  today: { type: String, default: '' },
  asOf: { type: Boolean, default: false },
})

const atajos = computed(() =>
  props.asOf
    ? fechasRapidas(props.fiscalYears, props.today)
    : periodosRapidos(props.fiscalYears, props.today),
)

const opciones = computed(() => [
  ...atajos.value.map((item) => ({ label: item.label, value: item.key })),
  { label: __('Personalizado'), value: 'custom' },
])

const atajo = computed({
  get() {
    const actual = atajos.value.find(
      (item) =>
        item.to === hasta.value && (props.asOf || item.from === desde.value),
    )
    return actual?.key || 'custom'
  },
  set(key) {
    const elegido = atajos.value.find((item) => item.key === key)
    if (!elegido) return
    if (!props.asOf) desde.value = elegido.from
    hasta.value = elegido.to
  },
})
</script>
