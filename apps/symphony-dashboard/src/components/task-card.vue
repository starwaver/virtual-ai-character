<script setup lang="ts">
import type { TaskCard } from '../shared/task'

import { GhostButton } from '@proj-airi/ui'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  task: TaskCard
}>()

const emit = defineEmits<{
  select: []
}>()

const { t } = useI18n()
</script>

<template>
  <GhostButton
    block
    size="unset"
    class="task-card text-left!"
    :aria-label="t('symphony.board.openTask', { identifier: props.task.issue.identifier })"
    @click="emit('select')"
  >
    <div class="w-full flex flex-col gap-3 p-3">
      <div class="flex items-start justify-between gap-2">
        <span class="text-primary-700 dark:text-primary-300 text-xs font-mono">{{ props.task.issue.identifier }}</span>
        <span v-if="props.task.stale" class="i-lucide-clock-3 text-orange-500" :aria-label="t('symphony.card.stale')" />
      </div>
      <h3 class="line-clamp-3 text-sm text-neutral-900 font-semibold dark:text-neutral-100">
        {{ props.task.issue.title }}
      </h3>
      <p v-if="props.task.progressSummary" class="line-clamp-3 text-xs text-neutral-600 dark:text-neutral-300">
        {{ props.task.progressSummary }}
      </p>
      <div class="flex flex-wrap gap-1.5">
        <span v-for="label in props.task.issue.labels" :key="label" class="rounded-full bg-neutral-200 px-2 py-0.5 text-[0.68rem] text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
          {{ label }}
        </span>
      </div>
      <div class="flex items-center justify-between gap-2 text-xs text-neutral-500 dark:text-neutral-400">
        <span v-if="props.task.agents.length" class="flex flex-wrap gap-1">
          <span v-for="agent in props.task.agents" :key="agent.id">{{ agent.name }} · {{ agent.role }}</span>
        </span>
        <span v-else>{{ t('symphony.card.noAgent') }}</span>
        <span v-if="props.task.counters.totalTokens !== null">{{ t('symphony.card.tokens', { count: props.task.counters.totalTokens }) }}</span>
      </div>
    </div>
  </GhostButton>
</template>

<style scoped>
.task-card {
  border: 1px solid rgb(var(--board-border) / 0.8);
  background: var(--board-card);
  box-shadow: 0 8px 24px rgb(15 23 42 / 0.08);
}

.task-card:hover {
  transform: translateY(-1px);
}
</style>
