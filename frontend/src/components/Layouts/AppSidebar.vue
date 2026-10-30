<template>
  <Sidebar
    v-model:collapsed="isSidebarCollapsed"
    :disable-collapse="mobile"
    :width="mobile ? '260px' : undefined"
    class="border-e border-outline-gray-1"
  >
    <div class="flex h-full flex-col p-2">
      <UserDropdown :is-collapsed="isCollapsed" />

      <ScrollArea class="mt-2 min-h-0 flex-1 -mx-2" viewport-class="px-2">
        <template v-for="section in navigation" :key="section.label || 'root'">
          <SidebarLabel
            v-if="section.label"
            divider
            class="mb-1 mt-4 select-none"
            :class="section.collapsible && !isCollapsed && 'cursor-pointer'"
            @click="section.collapsible && toggleSection(section.label)"
          >
            <span
              v-if="section.collapsible && !isCollapsed"
              class="flex items-center gap-1.5"
            >
              <LucideChevronRight
                class="size-4 shrink-0 text-ink-gray-7 transition-transform duration-200 -ml-0.5"
                :class="{ 'rotate-90': isSectionOpen(section.label) }"
              />
              <span class="truncate">{{ __(section.label) }}</span>
            </span>
            <span v-else class="truncate">{{ __(section.label) }}</span>
          </SidebarLabel>

          <nav
            v-if="!section.label || isSectionOpen(section.label) || isCollapsed"
            class="flex flex-col gap-0.5"
          >
            <SidebarItem
              v-for="item in section.items"
              :key="item.name"
              :to="{ name: item.name }"
              :label="__(item.label)"
              :active="route.name === item.name"
              @click="onNavigate"
            >
              <template #prefix>
                <component
                  :is="item.icon"
                  class="size-4 shrink-0 text-ink-gray-7"
                />
              </template>
            </SidebarItem>
          </nav>
        </template>
      </ScrollArea>

      <div v-if="!mobile" class="mt-auto flex flex-col gap-1 pt-2">
        <SidebarCollapseToggle />
      </div>
    </div>
  </Sidebar>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ScrollArea,
  Sidebar,
  SidebarCollapseToggle,
  SidebarItem,
  SidebarLabel,
} from 'frappe-ui'
import UserDropdown from '@/components/UserDropdown.vue'
import { navigation } from '@/navigation'
import LucideChevronRight from '~icons/lucide/chevron-right'

const props = defineProps({
  mobile: { type: Boolean, default: false },
})

const emit = defineEmits(['navigate'])

const route = useRoute()
const isSidebarCollapsed = ref(false)
const isCollapsed = computed(() => !props.mobile && isSidebarCollapsed.value)

const openSections = reactive({})

function ensureSectionDefaults() {
  for (const section of navigation) {
    if (section.label && section.collapsible && openSections[section.label] === undefined) {
      openSections[section.label] = true
    }
  }
}

ensureSectionDefaults()

function isSectionOpen(label) {
  if (!label) return true
  return openSections[label] !== false
}

function toggleSection(label) {
  openSections[label] = !isSectionOpen(label)
}

function openSectionForRoute(routeName) {
  for (const section of navigation) {
    if (!section.label || !section.collapsible) continue
    if (section.items.some((item) => item.name === routeName)) {
      openSections[section.label] = true
    }
  }
}

watch(
  () => route.name,
  (name) => {
    if (name) openSectionForRoute(name)
  },
  { immediate: true },
)

function onNavigate() {
  emit('navigate')
}
</script>
