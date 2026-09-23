<script setup lang="ts">
import type { TaskCard } from '../shared/task'

import { GhostButton } from '@proj-airi/ui'
import { useI18n } from 'vue-i18n'

import EventTimeline from './event-timeline.vue'

import { statusLabelKey } from '../composables/use-dashboard'

const props = defineProps<{
  task: TaskCard
}>()

const emit = defineEmits<{
  close: []
}>()

const { t } = useI18n()

function value(value: string | number | null): string {
  return value === null ? t('symphony.details.unavailable') : String(value)
}
</script>

<template>
  <aside class="details-panel" aria-labelledby="task-details-title">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="text-primary-700 dark:text-primary-300 text-xs font-mono">
          {{ props.task.issue.identifier }}
        </p>
        <h2 id="task-details-title" class="mt-1 text-lg text-neutral-900 font-semibold dark:text-neutral-100">
          {{ props.task.issue.title }}
        </h2>
      </div>
      <GhostButton size="sm" :aria-label="t('symphony.actions.close')" @click="emit('close')">
        <span class="i-lucide-x" aria-hidden="true" />
      </GhostButton>
    </div>

    <a v-if="props.task.issue.url" class="text-primary-700 dark:text-primary-300 text-xs underline" :href="props.task.issue.url" target="_blank" rel="noreferrer">
      {{ props.task.issue.url }}
    </a>

    <div class="flex flex-wrap gap-2">
      <span class="status-chip">{{ t(statusLabelKey(props.task.status)) }}</span>
      <span v-if="props.task.missingFromSource" class="status-chip status-chip-warning">{{ t('symphony.card.missing') }}</span>
      <span v-if="props.task.issue.trackerState" class="status-chip">{{ props.task.issue.trackerState }}</span>
    </div>

    <p v-if="props.task.progressSummary" class="rounded-lg bg-neutral-100 p-3 text-sm text-neutral-700 dark:bg-neutral-900 dark:text-neutral-200">
      {{ props.task.progressSummary }}
    </p>

    <dl class="details-grid">
      <div><dt>{{ t('symphony.details.agent') }}</dt><dd><span v-for="agent in props.task.agents" :key="agent.id" class="block">{{ agent.name }} · {{ agent.role }}</span><span v-if="!props.task.agents.length">{{ t('symphony.details.unavailable') }}</span></dd></div>
      <div><dt>{{ t('symphony.details.currentTask') }}</dt><dd>{{ value(props.task.currentTask) }}</dd></div>
      <div><dt>{{ t('symphony.details.role') }}</dt><dd>{{ props.task.agents[0]?.role ?? t('symphony.details.unavailable') }}</dd></div>
      <div><dt>{{ t('symphony.details.model') }}</dt><dd>{{ value(props.task.agents[0]?.modelRoute ?? null) }}</dd></div>
      <div><dt>{{ t('symphony.details.started') }}</dt><dd>{{ value(props.task.startedAt) }}</dd></div>
      <div><dt>{{ t('symphony.details.lastUpdated') }}</dt><dd>{{ value(props.task.lastUpdatedAt) }}</dd></div>
      <div><dt>{{ t('symphony.details.latestEvent') }}</dt><dd>{{ props.task.latestEvent?.type ?? t('symphony.details.unavailable') }}</dd></div>
      <div><dt>{{ t('symphony.details.branch') }}</dt><dd>{{ value(props.task.branch) }}</dd></div>
      <div><dt>{{ t('symphony.details.workspace') }}</dt><dd>{{ value(props.task.workspace) }}</dd></div>
      <div><dt>{{ t('symphony.details.pullRequest') }}</dt><dd><a v-if="props.task.pullRequestUrl" :href="props.task.pullRequestUrl" target="_blank" rel="noreferrer">{{ props.task.pullRequestUrl }}</a><span v-else>{{ t('symphony.details.unavailable') }}</span></dd></div>
      <div><dt>{{ t('symphony.details.turns') }}</dt><dd>{{ value(props.task.counters.turns) }}</dd></div>
      <div><dt>{{ t('symphony.details.retries') }}</dt><dd>{{ value(props.task.counters.retries) }}</dd></div>
      <div><dt>{{ t('symphony.details.runtime') }}</dt><dd>{{ value(props.task.counters.runtimeMs) }}</dd></div>
      <div><dt>{{ t('symphony.details.tokens') }}</dt><dd>{{ value(props.task.counters.totalTokens) }}</dd></div>
      <div><dt>{{ t('symphony.details.error') }}</dt><dd>{{ value(props.task.errorCode) }}</dd></div>
      <div><dt>{{ t('symphony.details.reviewerDecision') }}</dt><dd>{{ value(props.task.reviewerDecision) }}</dd></div>
    </dl>

    <EventTimeline :events="props.task.events" />
  </aside>
</template>

<style scoped>
.details-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: calc(100vh - 3rem);
  overflow-y: auto;
  border-radius: 1rem;
  background: var(--board-card);
  padding: 1.25rem;
  box-shadow: 0 16px 40px rgb(15 23 42 / 0.15);
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.details-grid dt {
  color: rgb(115 115 115);
  font-size: 0.68rem;
  text-transform: uppercase;
}

.details-grid dd {
  overflow-wrap: anywhere;
  color: rgb(38 38 38);
  font-size: 0.8rem;
}

.dark .details-grid dd {
  color: rgb(229 229 229);
}

.status-chip {
  border-radius: 999px;
  background: rgb(226 232 240 / 0.7);
  padding: 0.25rem 0.6rem;
  font-size: 0.7rem;
  font-weight: 600;
}

.status-chip-warning {
  background: rgb(254 215 170 / 0.75);
  color: rgb(154 52 18);
}

@media (max-width: 560px) {
  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
