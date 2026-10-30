<template>
  <div class="overflow-x-auto print:overflow-visible">
    <table class="w-full min-w-[1000px] border-collapse text-base">
      <thead>
        <tr
          class="border-b border-outline-gray-1 bg-surface-gray-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
        >
          <th class="w-28 px-4 py-2.5 text-left">{{ __('Fecha') }}</th>
          <th class="w-20 px-3 py-2.5 text-right">{{ __('Asiento') }}</th>
          <th class="w-48 px-3 py-2.5 text-left">{{ __('Documento') }}</th>
          <th class="px-3 py-2.5 text-left">{{ __('Concepto') }}</th>
          <th class="px-3 py-2.5 text-left">{{ __('Contrapartida') }}</th>
          <th class="w-32 px-3 py-2.5 text-right">{{ __('Debe') }}</th>
          <th class="w-32 px-3 py-2.5 text-right">{{ __('Haber') }}</th>
          <th class="w-36 px-4 py-2.5 text-right">{{ __('Saldo') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-outline-gray-1 bg-surface-amber-1 text-sm">
          <td class="px-4 py-2 font-medium text-ink-gray-7" colspan="5">
            {{
              cuenta.pyg
                ? __('Saldo al inicio del ejercicio y del periodo')
                : __('Saldo anterior')
            }}
          </td>
          <td colspan="2" />
          <td
            class="whitespace-nowrap px-4 py-2 text-right font-semibold tabular-nums text-ink-gray-9"
          >
            {{ saldo(cuenta.saldo_inicial) }}
          </td>
        </tr>
        <tr
          v-for="mov in filtrados"
          :key="mov.name"
          class="group cursor-pointer border-b border-outline-gray-1 hover:bg-surface-blue-1"
          @click="openDesk(mov.voucher_type, mov.voucher_no)"
        >
          <td
            class="whitespace-nowrap px-4 py-1.5 tabular-nums text-ink-gray-8"
          >
            {{ formatDate(mov.posting_date) }}
          </td>
          <td class="px-3 py-1.5 text-right tabular-nums text-ink-gray-5">
            {{ mov.asiento || '' }}
          </td>
          <td class="max-w-[14rem] px-3 py-1.5">
            <div class="flex min-w-0 flex-col">
              <span
                class="truncate text-sm font-medium text-ink-gray-8 group-hover:text-ink-blue-7"
                >{{ mov.voucher_no }}</span
              >
              <span class="truncate text-xs text-ink-gray-5">{{
                mov.voucher_label
              }}</span>
            </div>
          </td>
          <td
            class="max-w-sm truncate px-3 py-1.5 text-sm text-ink-gray-6"
            :title="mov.concepto"
          >
            {{ mov.concepto || mov.tercero }}
          </td>
          <td
            class="max-w-[16rem] truncate px-3 py-1.5 text-sm text-ink-gray-6"
            :title="mov.contrapartida"
          >
            {{ mov.contrapartida }}
            <span v-if="mov.contrapartidas > 1" class="text-ink-gray-4"
              >+{{ mov.contrapartidas - 1 }}</span
            >
          </td>
          <td
            class="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-ink-gray-9"
          >
            {{ mov.debit ? formatImporte(mov.debit) : '' }}
          </td>
          <td
            class="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-ink-gray-9"
          >
            {{ mov.credit ? formatImporte(mov.credit) : '' }}
          </td>
          <td
            class="whitespace-nowrap px-4 py-1.5 text-right tabular-nums"
            :class="mov.balance < 0 ? 'text-ink-red-7' : 'text-ink-gray-8'"
          >
            {{ saldo(mov.balance) }}
          </td>
        </tr>
        <tr v-if="!filtrados.length">
          <td
            colspan="8"
            class="px-4 py-8 text-center text-base text-ink-gray-5"
          >
            {{
              busqueda
                ? __('Ningún movimiento coincide con la búsqueda')
                : __('Sin movimientos en el periodo')
            }}
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr
          class="border-t-2 border-outline-gray-3 bg-surface-gray-2 font-semibold text-ink-gray-9"
        >
          <td colspan="5" class="px-4 py-2.5 uppercase tracking-wide">
            {{ busqueda ? __('Total filtrado') : __('Totales y saldo final') }}
          </td>
          <td class="whitespace-nowrap px-3 py-2.5 text-right tabular-nums">
            {{ formatImporte(totalDebe) }}
          </td>
          <td class="whitespace-nowrap px-3 py-2.5 text-right tabular-nums">
            {{ formatImporte(totalHaber) }}
          </td>
          <td class="whitespace-nowrap px-4 py-2.5 text-right tabular-nums">
            {{ busqueda ? '' : saldo(cuenta.saldo_final) }}
          </td>
        </tr>
      </tfoot>
    </table>
    <p v-if="cuenta.truncated" class="px-4 py-2 text-sm text-ink-amber-8">
      {{
        __(
          'Se muestran {0} de {1} movimientos. Acote el periodo para ver el resto.',
          formatNumber(cuenta.movimientos.length, 0),
          formatNumber(cuenta.n_movimientos, 0),
        )
      }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  formatDate,
  formatImporte,
  formatNumber,
  openDesk,
} from '@/composables/informe'

const props = defineProps({
  cuenta: { type: Object, required: true },
  busqueda: { type: String, default: '' },
})

const filtrados = computed(() => {
  const texto = props.busqueda.trim().toLowerCase()
  if (!texto) return props.cuenta.movimientos
  return props.cuenta.movimientos.filter((mov) =>
    [
      mov.voucher_no,
      mov.concepto,
      mov.contrapartida,
      mov.tercero,
      mov.voucher_label,
    ]
      .filter(Boolean)
      .some((valor) => String(valor).toLowerCase().includes(texto)),
  )
})

const totalDebe = computed(() =>
  props.busqueda
    ? filtrados.value.reduce((s, m) => s + (m.debit || 0), 0)
    : props.cuenta.debe,
)
const totalHaber = computed(() =>
  props.busqueda
    ? filtrados.value.reduce((s, m) => s + (m.credit || 0), 0)
    : props.cuenta.haber,
)

function saldo(valor) {
  const v = Number(valor) || 0
  if (Math.abs(v) < 0.005) return '0,00'
  return `${formatImporte(Math.abs(v))} ${v > 0 ? 'D' : 'H'}`
}
</script>
