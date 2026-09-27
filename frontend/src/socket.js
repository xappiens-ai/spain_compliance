import { io } from 'socket.io-client'
import { getCachedListResource, getCachedDocumentResource } from 'frappe-ui'

export function initSocket() {
  let host = window.location.hostname
  let siteName = window.site_name || host
  let port = window.socketio_port || 9000
  let protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  let url =
    window.location.port === String(port) || import.meta.env.DEV
      ? `${protocol}://${host}:${port}/${siteName}`
      : `${protocol}://${host}/${siteName}`

  let socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })

  socket.on('refetch_resource', (data) => {
    if (data.cache_key) {
      let resource =
        getCachedListResource(data.cache_key) ||
        getCachedDocumentResource(data.cache_key)
      if (resource?.reload) {
        resource.reload()
      }
    }
  })

  return socket
}
