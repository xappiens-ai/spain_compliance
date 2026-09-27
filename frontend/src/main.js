import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  FrappeUI,
  Button,
  Dialog,
  Badge,
  ErrorMessage,
  FormControl,
  setConfig,
  frappeRequest,
} from 'frappe-ui'
import { spritePlugin } from 'frappe-ui/icons'

import App from './App.vue'
import router from './router'
import translationPlugin from './translation'
import { initSocket } from './socket'

let pinia = createPinia()
let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(FrappeUI)
app.use(spritePlugin)
app.use(pinia)
app.use(router)
app.use(translationPlugin)

const globalComponents = {
  Button,
  Dialog,
  Badge,
  ErrorMessage,
  FormControl,
}

for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}

function mountApp() {
  let socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
}

if (import.meta.env.DEV) {
  frappeRequest({
    url: '/api/method/spain_compliance.www.contabilidad.get_context_for_dev',
  }).then((values) => {
    for (let key in values) {
      window[key] = values[key]
    }
    mountApp()
  })
} else {
  mountApp()
}
