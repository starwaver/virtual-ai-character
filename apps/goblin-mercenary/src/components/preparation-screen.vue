<script setup lang="ts">
import type { CrewId, GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import CharacterArt from './character-art.vue'
import LocationArt from './location-art.vue'
import ResourceBar from './resource-bar.vue'
import RosterList from './roster-list.vue'

import { getContracts } from '../game'

const props = defineProps<{
  state: GameState
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()

const selectedCrew = computed(() => props.state.activeCrew)
const contract = computed(() => getContracts().find(item => item.id === props.state.selectedContract) ?? null)
const mog = computed(() => props.state.crew.mog)
const mogBadlyWounded = computed(() => mog.value.health > 0 && mog.value.health <= Math.floor(mog.value.maxHealth / 2))
const canLaunch = computed(() => selectedCrew.value.length === 2 && props.state.resources.rations >= (contract.value?.rationCost ?? Number.MAX_SAFE_INTEGER))
const canBuyRations = computed(() => props.state.resources.coin >= 2)

function toggleCrew(id: CrewId) {
  const hasCrew = selectedCrew.value.includes(id)
  const nextCrew = hasCrew
    ? selectedCrew.value.filter(member => member !== id)
    : [...selectedCrew.value, id]

  if (nextCrew.length > 2)
    return

  emit('command', { type: 'select-crew', crew: nextCrew })
}
</script>

<template>
  <div :class="['game-page', 'px-4 py-5 sm:px-8 sm:py-8']">
    <div :class="['game-layout', 'mx-auto max-w-7xl space-y-6']">
      <ResourceBar :state="state" />

      <header class="page-heading">
        <Button
          color="amber"
          variant="secondary"
          type="button"
          @click="emit('command', { type: 'leave-preparation' })"
        >
          Back to contract board
        </Button>
        <p class="eyebrow">
          Preparation
        </p>
        <h1 :class="['mt-2 text-4xl leading-tight sm:text-5xl']">
          {{ contract?.name ?? 'Choose your crew' }}
        </h1>
        <p :class="['mt-2 max-w-3xl text-base leading-relaxed', 'text-muted']">
          Select two healthy crew members. Your choice sets the tools you can use in battle.
        </p>
      </header>

      <section v-if="contract" class="preparation-scene" aria-label="Selected crew">
        <LocationArt :location="contract.id" />
        <div class="marching-crew">
          <div v-for="id in selectedCrew" :key="id" class="marching-member">
            <CharacterArt :character="id" />
            <span>{{ state.crew[id].name }}</span>
          </div>
          <div v-for="slot in 2 - selectedCrew.length" :key="`empty-${slot}`" class="empty-crew-slot" aria-hidden="true">
            +
          </div>
        </div>
        <p class="preparation-scene-label">
          {{ selectedCrew.length }} / 2 selected · {{ contract.name }}
        </p>
      </section>

      <div :class="['preparation-grid', 'grid gap-6 xl:grid-cols-[1.4fr_0.8fr]']">
        <section :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="crew-choice-title">
          <div :class="['flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between']">
            <div>
              <p class="eyebrow">
                Active crew
              </p>
              <h2 id="crew-choice-title" :class="['mt-1 text-2xl font-semibold']">
                Choose exactly two
              </h2>
            </div>
            <p class="selection-count" aria-live="polite">
              {{ selectedCrew.length }} / 2 selected
            </p>
          </div>
          <p :class="['mt-2 mb-5 text-sm leading-relaxed', 'text-muted']">
            The Captain is available for a flexible strike. Pick a specialist to change your options.
          </p>
          <RosterList
            :state="state"
            :selectable="true"
            :selected-crew="selectedCrew"
            @select="toggleCrew"
          />
          <p v-if="mogBadlyWounded" :class="['healer-advice', 'mt-5 rounded-2xl p-4 leading-relaxed']">
            <strong>Mog is badly wounded.</strong>
            Bring Mara to restore his health in battle. Grit’s bomb can end a threat faster, but it cannot protect Mog.
          </p>
          <p v-else-if="mog.health === 0" :class="['warning-note', 'mt-5 rounded-2xl p-4 leading-relaxed']">
            Mog is out of action. Choose two healthy crew members for this job.
          </p>
          <p v-else :class="['preparation-tip', 'mt-5 rounded-2xl p-4 leading-relaxed']">
            Mara can heal one crew member once. Grit can spend one bomb for a powerful strike. Choose the help this contract needs.
          </p>
        </section>

        <aside :class="['flex flex-col gap-6']">
          <section :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="job-brief-title">
            <p class="eyebrow">
              Job brief
            </p>
            <h2 id="job-brief-title" :class="['mt-1 text-2xl font-semibold']">
              {{ contract?.enemyName ?? 'No threat selected' }}
            </h2>
            <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
              {{ contract?.description ?? 'Return to the contract board to choose a job.' }}
            </p>
            <div :class="['job-cost', 'mt-5 flex items-center justify-between gap-4 rounded-2xl p-4']">
              <div>
                <p class="small-label">
                  Rations needed
                </p>
                <p :class="['mt-1 text-xl font-semibold']">
                  {{ contract?.rationCost ?? 0 }} ration
                </p>
              </div>
              <p :class="['text-right text-sm', 'text-muted']">
                {{ state.resources.rations }} in pack
              </p>
            </div>
            <Button
              :class="['mt-4 w-full']"
              :disabled="!canBuyRations"
              color="amber"
              variant="secondary"
              type="button"
              @click="emit('command', { type: 'buy-rations', amount: 1 })"
            >
              Buy one ration · 2 gold
            </Button>
            <p v-if="!canBuyRations" :class="['mt-2 text-sm', 'text-muted']">
              Nix has no gold left for another ration.
            </p>
            <p v-else :class="['mt-2 text-sm', 'text-muted']">
              A ration pays the crew’s cost before the fight.
            </p>
          </section>

          <section :class="['launch-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="launch-title">
            <p class="eyebrow">
              Nix’s note
            </p>
            <h2 id="launch-title" :class="['mt-1 text-xl font-semibold']">
              “Two goblins, one plan. That is already above budget.”
            </h2>
            <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
              The next threat is predictable. Watch who it targets and choose whether to strike or save a crew member.
            </p>
            <Button
              :class="['mt-5 w-full']"
              color="primary"
              variant="primary"
              size="lg"
              :disabled="!canLaunch"
              type="button"
              @click="emit('command', { type: 'launch-encounter' })"
            >
              {{ state.resources.rations < (contract?.rationCost ?? 0) ? 'Buy rations to launch' : 'Launch the contract' }}
            </Button>
            <p v-if="selectedCrew.length !== 2" :class="['mt-3 text-sm', 'text-muted']">
              Select two healthy crew members to continue.
            </p>
            <p v-else-if="state.resources.rations < (contract?.rationCost ?? 0)" :class="['mt-3 text-sm', 'text-muted']">
              Buy enough rations before the crew sets out.
            </p>
          </section>
        </aside>
      </div>
    </div>
  </div>
</template>
