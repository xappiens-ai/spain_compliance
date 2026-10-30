<template>
  <div ref="contenedor" class="h-full w-full" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { init } from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
})
const emit = defineEmits(['click'])

const contenedor = ref(null)
const grafico = shallowRef(null)
let observador = null

onMounted(() => {
  grafico.value = init(contenedor.value, null, { renderer: 'svg' })
  grafico.value.setOption(props.option, true)
  grafico.value.on('click', (params) => emit('click', params))
  observador = new ResizeObserver(() => grafico.value?.resize())
  observador.observe(contenedor.value)
})

watch(
  () => props.option,
  (option) => grafico.value?.setOption(option, true),
)

onBeforeUnmount(() => {
  observador?.disconnect()
  grafico.value?.dispose()
})
</script>
