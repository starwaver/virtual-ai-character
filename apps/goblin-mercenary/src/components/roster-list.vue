<script setup lang="ts">
import type { CrewId, CrewRole, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import { CREW_IDS } from '../game'

const props = withDefaults(defineProps<{
  state: GameState
  selectable?: boolean
  selectedCrew?: CrewId[]
}>(), {
  selectable: false,
})

const emit = defineEmits<{
  select: [crewId: CrewId]
}>()

const crew = computed(() => CREW_IDS.map(id => props.state.crew[id]))
const roleLabels: Record<CrewRole, string> = {
  captain: 'Captain',
  lieutenant: 'Lieutenant',
  quartermaster: 'Quartermaster',
  fighter: 'Front line',
  healer: 'Healer',
  bomber: 'Bomber',
}

function rolesFor(roles: CrewRole[]): string {
  return roles.map(role => roleLabels[role]).join(' · ')
}

function healthPercent(id: CrewId): number {
  const member = props.state.crew[id]
  return (member.health / member.maxHealth) * 100
}

function isSelected(id: CrewId): boolean {
  return props.selectedCrew?.includes(id) ?? false
}

function isUnavailable(id: CrewId): boolean {
  return props.state.crew[id].health === 0
}

function isSelectionLimitReached(id: CrewId): boolean {
  return (props.selectedCrew?.length ?? 0) >= 2 && !isSelected(id)
}
</script>

<template>
  <ul :class="['roster-list', 'grid gap-3']">
    <li v-for="member in crew" :key="member.id">
      <article
        :class="[
          'roster-card',
          'rounded-2xl p-4',
          isSelected(member.id) && 'roster-card-selected',
          isUnavailable(member.id) && 'roster-card-unavailable',
        ]"
      >
        <div :class="['flex items-start gap-3']">
          <span :class="['crew-token', 'grid h-11 w-11 shrink-0 place-items-center rounded-full text-lg font-semibold']" aria-hidden="true">
            {{ member.name.slice(0, 1) }}
          </span>
          <div :class="['min-w-0 flex-1']">
            <div :class="['flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1']">
              <h3 :class="['font-semibold']">
                {{ member.name }}
              </h3>
              <span class="health-value">{{ member.health }} / {{ member.maxHealth }}</span>
            </div>
            <p :class="['mt-1 text-xs leading-relaxed', 'copy-muted']">
              {{ rolesFor(member.roles) }}
            </p>
          </div>
        </div>
        <div
          :class="['crew-health-track', 'mt-3 h-2 overflow-hidden rounded-full']"
          role="meter"
          :aria-valuenow="member.health"
          :aria-valuemin="0"
          :aria-valuemax="member.maxHealth"
          :aria-valuetext="`${member.health} of ${member.maxHealth} health`"
          :aria-label="`${member.name} health`"
        >
          <div class="crew-health-fill h-full rounded-full" :style="{ width: `${healthPercent(member.id)}%` }" />
        </div>
        <div v-if="selectable" :class="['mt-3 flex items-center justify-between gap-3']">
          <span v-if="isUnavailable(member.id)" class="small-label">Unavailable</span>
          <span v-else-if="isSelected(member.id)" class="selection-label">Selected</span>
          <span v-else-if="isSelectionLimitReached(member.id)" class="small-label">Choose two crew</span>
          <span v-else class="small-label">Ready for duty</span>
          <Button
            :class="['shrink-0']"
            size="sm"
            :disabled="isUnavailable(member.id) || isSelectionLimitReached(member.id)"
            :color="isSelected(member.id) ? 'primary' : 'neutral'"
            :variant="isSelected(member.id) ? 'primary' : 'secondary'"
            :aria-label="(isSelected(member.id) ? 'Remove ' : 'Select ') + member.name"
            :aria-pressed="isSelected(member.id)"
            type="button"
            @click="emit('select', member.id)"
          >
            {{ isSelected(member.id) ? 'Remove' : 'Select' }}
          </Button>
        </div>
      </article>
    </li>
  </ul>
</template>
