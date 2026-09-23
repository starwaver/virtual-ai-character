import { resolve } from 'node:path'

import Vue from '@vitejs/plugin-vue'
import Unocss from 'unocss/vite'
import Yaml from 'unplugin-yaml/vite'

import { defineConfig } from 'vite'

export default defineConfig({
  resolve: {
    alias: {
      '@proj-airi/i18n': resolve(import.meta.dirname, '..', '..', 'packages', 'i18n', 'src'),
    },
  },
  plugins: [
    Vue(),
    Unocss(),
    Yaml(),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
