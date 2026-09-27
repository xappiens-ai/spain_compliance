<template>
  <FrappeUIProvider>
    <Layout v-if="session.isLoggedIn" class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent, provide } from 'vue'
import { FrappeUIProvider, setConfig, useTheme } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

const session = sessionStore()
provide('session', session)

const { setTheme } = useTheme()
if (!localStorage.getItem('theme')) {
  setTheme('light')
}

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
