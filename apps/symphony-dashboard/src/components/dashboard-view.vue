<script setup lang="ts">
import { Button } from '@proj-airi/ui'
import { computed, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'

import ConnectionStatus from './connection-status.vue'
import KanbanBoard from './kanban-board.vue'
import TaskDetails from './task-details.vue'

import { useDashboard } from '../composables/use-dashboard'

const { columns, errorCode, lastRefreshAt, loading, refresh, stale, state, tasks } = useDashboard()
const selectedKey = shallowRef<string | null>(null)
const selectedTask = computed(() => tasks.value.find(task => task.key === selectedKey.value) ?? null)
const { t } = useI18n()

function selectTask(task: { key: string }) {
  selectedKey.value = task.key
}

function closeDetails() {
  selectedKey.value = null
}
</script>

<template>
  <main class="dashboard-shell">
    <header class="dashboard-header">
      <div>
        <p class="text-primary-700 dark:text-primary-300 text-xs font-semibold tracking-[0.2em] uppercase">
          {{ t('symphony.dashboard.eyebrow') }}
        </p>
        <h1 class="mt-2 text-3xl text-neutral-950 font-semibold dark:text-white">
          {{ t('symphony.dashboard.title') }}
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-neutral-600 dark:text-neutral-300">
          {{ t('symphony.dashboard.description') }}
        </p>
      </div>
      <Button class="refresh-button" size="sm" :loading="loading" @click="refresh">
        <span class="i-lucide-refresh-cw" aria-hidden="true" />
        {{ t('symphony.actions.refresh') }}
      </Button>
    </header>

    <ConnectionStatus
      :state="state"
      :error-code="errorCode"
      :last-refresh-at="lastRefreshAt"
      :stale="stale"
      :loading="loading"
      @refresh="refresh"
    />

    <div class="dashboard-content" :class="selectedTask && 'has-details'">
      <KanbanBoard :columns="columns" @select="selectTask" />
      <TaskDetails v-if="selectedTask" :task="selectedTask" @close="closeDetails" />
    </div>
  </main>
</template>

<style scoped>
.dashboard-shell {
  --board-surface: 241 245 249;
  --board-card: rgb(255 255 255 / 0.82);
  --board-border: 203 213 225;
  min-height: 100vh;
  background:
    radial-gradient(circle at 10% 0%, rgb(186 230 253 / 0.5), transparent 35rem),
    rgb(248 250 252);
  color: rgb(15 23 42);
  padding: 1.5rem;
}

.dashboard-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin: 0 auto 1.5rem;
  max-width: 1800px;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1rem auto 0;
  max-width: 1800px;
}

.dashboard-content.has-details {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(19rem, 24rem);
  align-items: start;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgb(14 116 144 / 0.25);
  border-radius: 0.75rem;
  background: rgb(255 255 255 / 0.75);
  padding: 0.6rem 0.9rem;
  color: rgb(14 116 144);
  font-size: 0.8rem;
  font-weight: 600;
}

.refresh-button:focus-visible {
  outline: 2px solid rgb(14 116 144);
  outline-offset: 2px;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.55;
}

.dark .dashboard-shell {
  --board-surface: 23 37 84;
  --board-card: rgb(15 23 42 / 0.86);
  --board-border: 51 65 85;
  background:
    radial-gradient(circle at 10% 0%, rgb(30 64 175 / 0.35), transparent 35rem),
    rgb(2 6 23);
  color: rgb(241 245 249);
}

.dark .refresh-button {
  border-color: rgb(56 189 248 / 0.35);
  background: rgb(15 23 42 / 0.75);
  color: rgb(125 211 252);
}

@media (max-width: 1100px) {
  .dashboard-content.has-details {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .dashboard-shell {
    padding: 1rem;
  }

  .dashboard-header {
    flex-direction: column;
  }

  .refresh-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
