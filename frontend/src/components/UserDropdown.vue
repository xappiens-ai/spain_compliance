<template>
  <Dropdown :options="dropdownItems">
    <template #default="{ open }">
      <button
        class="flex h-12 items-center rounded-md py-2 duration-300 ease-in-out"
        :class="
          isCollapsed
            ? 'w-auto px-0'
            : open
              ? 'w-full px-2 bg-surface-elevation-3 shadow-sm'
              : 'w-full px-2 hover:bg-surface-gray-2'
        "
      >
        <img
          :src="logoUrl"
          alt="Contabilidad"
          class="h-8 w-8 flex-shrink-0 rounded-md"
        />
        <div
          class="flex flex-1 flex-col text-left duration-300 ease-in-out truncate"
          :class="
            isCollapsed
              ? 'ml-0 w-0 overflow-hidden opacity-0'
              : 'ml-2 w-auto opacity-100'
          "
        >
          <div
            class="text-base font-medium leading-none text-ink-gray-9 truncate"
          >
            {{ __('Contabilidad') }}
          </div>
          <div class="mt-1 text-sm leading-none text-ink-gray-7 truncate">
            {{ userFullName }}
          </div>
        </div>
        <div
          class="duration-300 ease-in-out"
          :class="
            isCollapsed
              ? 'ml-0 w-0 overflow-hidden opacity-0'
              : 'ml-2 w-auto opacity-100'
          "
        >
          <LucideChevronDown class="size-4 text-ink-gray-5" />
        </div>
      </button>
    </template>
  </Dropdown>
</template>

<script setup>
import { computed, h, markRaw } from 'vue'
import { Dropdown } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import logoUrl from '@/assets/logo.svg'

import LucideLayoutGrid from '~icons/lucide/layout-grid'
import LucideLogOut from '~icons/lucide/log-out'
import LucideChevronDown from '~icons/lucide/chevron-down'

defineProps({
  isCollapsed: { type: Boolean, default: false },
})

const session = sessionStore()

const userFullName = computed(
  () => window.user?.full_name || session.user || __('Usuario'),
)

const dropdownItems = computed(() => [
  {
    group: __('Apps'),
    items: [
      {
        label: __('Escritorio Frappe'),
        icon: () => h(markRaw(LucideLayoutGrid), { class: 'size-4' }),
        onClick: () => {
          window.location.href = '/app'
        },
      },
    ],
  },
  {
    group: __('Cuenta'),
    items: [
      {
        label: __('Cerrar sesión'),
        icon: () => h(markRaw(LucideLogOut), { class: 'size-4' }),
        onClick: () => session.logout.submit(),
      },
    ],
  },
])
</script>
