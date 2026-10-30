<template>
  <FrappeUIProvider>
    <Layout v-if="session.isLoggedIn" class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent, provide } from 'vue'
import { FrappeUIProvider, setConfig } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

const session = sessionStore()
provide('session', session)

// Solo hay tema claro. useTheme() seguiría al sistema operativo y escribiría
// localStorage('theme'), que comparten las demás SPAs del sitio (CRM, Helpdesk…).
document.documentElement.setAttribute('data-theme', 'light')

const DesktopLayout = defineAsyncComponent(
  () => import('@/components/Layouts/DesktopLayout.vue'),
)
const MobileLayout = defineAsyncComponent(
  () => import('@/components/Layouts/MobileLayout.vue'),
)

const Layout = computed(() =>
  window.innerWidth < 640 ? MobileLayout : DesktopLayout,
)

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
setConfig('translatedMessages', window.translated_messages || {})
</script>
