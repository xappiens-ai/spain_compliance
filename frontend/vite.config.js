import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        outDir: '../spain_compliance/public/frontend',
        indexHtmlPath: '../spain_compliance/www/contabilidad.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
    vue(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    dedupe: ['vue', 'vue-router', 'frappe-ui'],
  },
  optimizeDeps: {
    include: ['tailwind.config.js'],
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, '../..')],
    },
  },
})
