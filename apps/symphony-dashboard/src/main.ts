import messages from '@proj-airi/i18n/locales/en/symphony.yaml'

import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'

import App from './app.vue'

import '@unocss/reset/tailwind.css'
import 'virtual:uno.css'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: { en: { symphony: messages } },
})

createApp(App).use(i18n).mount('#app')
