<template>
  <Alert
    v-if="avisos.length"
    theme="yellow"
    :title="
      __('{0} cuentas fuera del cuadro del PGC o sin número', avisos.length)
    "
  >
    <template #description>
      <ul class="list-disc space-y-1 pl-5">
        <li v-for="aviso in visibles" :key="aviso">{{ aviso }}</li>
      </ul>
      <Button
        v-if="avisos.length > LIMITE"
        class="mt-2"
        size="sm"
        variant="ghost"
        :label="todos ? __('Ver menos') : __('Ver las {0}', avisos.length)"
        @click="todos = !todos"
      />
    </template>
  </Alert>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Alert, Button } from 'frappe-ui'

const LIMITE = 8

const props = defineProps({
  avisos: { type: Array, default: () => [] },
})

const todos = ref(false)
const visibles = computed(() =>
  todos.value ? props.avisos : props.avisos.slice(0, LIMITE),
)
</script>
