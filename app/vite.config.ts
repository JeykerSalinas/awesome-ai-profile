import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import ui from '@nuxt/ui/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue(),
    ui({
      ui: {
        colors: {
          primary: 'red',
          neutral: 'stone',
        },
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
