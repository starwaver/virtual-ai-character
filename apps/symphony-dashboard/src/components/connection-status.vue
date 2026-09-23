<script setup lang="ts">
import type { DashboardConnectionState } from '../composables/use-dashboard'

import { Button, Callout } from '@proj-airi/ui'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  state: DashboardConnectionState
  errorCode: string | null
  lastRefreshAt: string | null
  stale: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

const { t } = useI18n()
</script>

<template>
  <Callout v-if="props.state === 'error' || props.state === 'stale'" theme="orange">
    <template #label>
      {{ props.state === 'stale' ? t('symphony.connection.stale') : t('symphony.connection.error') }}
    </template>
    <div class="flex flex-wrap items-center justify-between gap-3 text-sm">
      <span>{{ props.errorCode ? t(`symphony.errors.${props.errorCode}`, props.errorCode) : t('symphony.connection.unavailable') }}</span>
      <Button size="sm" color="orange" @click="emit('refresh')">
        <span class="i-lucide-refresh-cw" aria-hidden="true" />
        {{ t('symphony.actions.refresh') }}
      </Button>
    </div>
  </Callout>
  <div v-else class="flex items-center justify-between gap-3 text-xs text-neutral-500 dark:text-neutral-400" aria-live="polite">
    <span v-if="props.state === 'loading'">{{ t('symphony.connection.loading') }}</span>
    <span v-else-if="props.state === 'empty'">{{ t('symphony.connection.empty') }}</span>
    <span v-else>{{ t('symphony.connection.updated', { time: props.lastRefreshAt ?? '—' }) }}</span>
    <span v-if="props.loading" class="i-lucide-loader-circle animate-spin" aria-label="Loading" />
  </div>
</template>
