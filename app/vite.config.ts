import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import ui from '@nuxt/ui/vite'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const profileId = process.env.VITE_PROFILE_ID || loadEnv(mode, process.cwd(), 'VITE_').VITE_PROFILE_ID || 'jeyker'
  if (!['jeyker', 'sara'].includes(profileId)) throw new Error('Unknown VITE_PROFILE_ID: ' + profileId)
  return {
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
  }
})
