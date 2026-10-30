<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __(title), route: $route.fullPath }]" />
    </template>
  </LayoutHeader>

  <EmptyState :title="title" :description="description" :icon="pageIcon" />
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/EmptyState.vue'

import LucideBookOpen from '~icons/lucide/book-open'
import LucideLayers from '~icons/lucide/layers'
import LucideSend from '~icons/lucide/send'
import LucideShieldCheck from '~icons/lucide/shield-check'
import LucideClipboardList from '~icons/lucide/clipboard-list'
import LucideSettings from '~icons/lucide/settings'
import LucideCircleAlert from '~icons/lucide/circle-alert'
import LucideBox from '~icons/lucide/box'
import LucideContact from '~icons/lucide/contact'
import LucideTrendingUp from '~icons/lucide/trending-up'
import LucideScale from '~icons/lucide/scale'
import LucideSigma from '~icons/lucide/sigma'

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, required: true },
  icon: { type: String, default: 'box' },
})

const icons = {
  'book-open': LucideBookOpen,
  layers: LucideLayers,
  send: LucideSend,
  'shield-check': LucideShieldCheck,
  'clipboard-list': LucideClipboardList,
  settings: LucideSettings,
  'circle-alert': LucideCircleAlert,
  box: LucideBox,
  contact: LucideContact,
  'trending-up': LucideTrendingUp,
  scale: LucideScale,
  sigma: LucideSigma,
}

const pageIcon = computed(() => markRaw(icons[props.icon] || LucideBox))
</script>
