import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { ref, computed } from 'vue'

export const sessionStore = defineStore('spain-compliance-session', () => {
  function sessionUser() {
    let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    let _sessionUser = cookies.get('user_id')
    if (_sessionUser === 'Guest') {
      _sessionUser = null
    }
    return _sessionUser
  }

  let user = ref(sessionUser() || window.user?.name || null)
  const isLoggedIn = computed(() => !!user.value)

  const logout = createResource({
    url: 'logout',
    onSuccess() {
      user.value = null
      window.location.href = '/login?redirect-to=/contabilidad'
    },
  })

  return {
    user,
    isLoggedIn,
    logout,
  }
})
