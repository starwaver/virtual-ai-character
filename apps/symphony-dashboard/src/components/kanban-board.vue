<script setup lang="ts">
import type { BoardColumn, TaskCard } from '../shared/task'

import { useI18n } from 'vue-i18n'

import TaskCardView from './task-card.vue'

defineProps<{
  columns: Array<{ column: BoardColumn, tasks: TaskCard[] }>
}>()

const emit = defineEmits<{
  select: [task: TaskCard]
}>()

const { t } = useI18n()
</script>

<template>
  <section class="board-grid" aria-label="Kanban board">
    <div v-for="entry in columns" :key="entry.column" class="board-column">
      <div class="mb-3 flex items-center justify-between gap-3">
        <h2 class="text-sm text-neutral-800 font-semibold dark:text-neutral-100">
          {{ t(`symphony.status.${entry.column}`) }}
        </h2>
        <span class="rounded-full bg-neutral-200 px-2 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
          {{ entry.tasks.length }}
        </span>
      </div>
      <div v-if="entry.tasks.length" class="flex flex-col gap-3">
        <TaskCardView
          v-for="task in entry.tasks"
          :key="task.key"
          :task="task"
          @select="emit('select', task)"
        />
      </div>
      <div v-else class="border border-neutral-300 rounded-xl border-dashed p-4 text-xs text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
        {{ t('symphony.board.emptyColumn') }}
      </div>
    </div>
  </section>
</template>

<style scoped>
.board-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(15rem, 1fr));
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.board-column {
  min-width: 15rem;
  min-height: 12rem;
  border-radius: 1rem;
  background: rgb(var(--board-surface) / 0.88);
  padding: 1rem;
}

@media (max-width: 900px) {
  .board-grid {
    grid-template-columns: repeat(2, minmax(15rem, 1fr));
    overflow-x: visible;
  }
}

@media (max-width: 560px) {
  .board-grid {
    grid-template-columns: 1fr;
  }

  .board-column {
    min-width: 0;
  }
}
</style>
