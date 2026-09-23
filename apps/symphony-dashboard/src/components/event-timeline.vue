<script setup lang="ts">
import type { TaskEvent } from '../shared/task'

import { useI18n } from 'vue-i18n'

defineProps<{
  events: TaskEvent[]
}>()

const { t } = useI18n()
</script>

<template>
  <section class="flex flex-col gap-2" :aria-label="t('symphony.details.timeline')">
    <h3 class="text-xs text-neutral-500 font-semibold tracking-wide uppercase dark:text-neutral-400">
      {{ t('symphony.details.timeline') }}
    </h3>
    <ol v-if="events.length" class="flex flex-col gap-2 border-l border-neutral-300 pl-4 dark:border-neutral-700">
      <li v-for="event in events" :key="event.id" class="relative text-xs text-neutral-700 dark:text-neutral-200">
        <span class="bg-primary-500 absolute top-1 h-2 w-2 rounded-full -left-[1.3rem]" aria-hidden="true" />
        <div class="font-medium">
          {{ event.type }}
        </div>
        <div v-if="event.summary" class="mt-0.5 text-neutral-500 dark:text-neutral-400">
          {{ event.summary }}
        </div>
        <time class="mt-0.5 block text-[0.68rem] text-neutral-400" :datetime="event.observedAt">{{ event.observedAt }}</time>
      </li>
    </ol>
    <p v-else class="text-xs text-neutral-500 dark:text-neutral-400">
      {{ t('symphony.details.noEvents') }}
    </p>
  </section>
</template>
