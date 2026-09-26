<script setup lang="ts">
import type { CrewId, GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed, shallowRef } from 'vue'

import BattleScene from './battle-scene.vue'
import ResourceBar from './resource-bar.vue'

import { getContracts, getNextThreatTarget } from '../game'

const props = defineProps<{
  state: GameState
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()

const contract = computed(() => getContracts().find(item => item.id === props.state.selectedContract) ?? null)
const encounter = computed(() => props.state.encounter)
const nextThreatTarget = computed(() => getNextThreatTarget(props.state))
const nextThreatName = computed(() => nextThreatTarget.value === null ? 'No crew member' : props.state.crew[nextThreatTarget.value].name)
const healingTargets = computed(() => props.state.activeCrew
  .filter(id => props.state.crew[id].health > 0 && props.state.crew[id].health < props.state.crew[id].maxHealth)
  .map(id => props.state.crew[id]))
const healerCanAct = computed(() => props.state.crew.healer.health > 0 && props.state.activeCrew.includes('healer'))
const bomberCanAct = computed(() => props.state.crew.bomber.health > 0 && props.state.activeCrew.includes('bomber'))
const combatStatus = computed(() => {
  if (encounter.value === null || contract.value === null)
    return 'The encounter is not ready.'

  const threat = nextThreatTarget.value === null
    ? 'No crew member can take the next threat.'
    : `${nextThreatName.value} faces ${contract.value.enemyAttack} damage next.`

  return `Round ${encounter.value.round + 1}. ${
    contract.value.enemyName} has ${encounter.value.enemyHealth} health. ${
    threat}`
})

// This snapshot belongs to the current encounter view only. It never enters the save.
const beforeAction = shallowRef<GameState>()
const healingTarget = shallowRef<CrewId>()

function perform(command: GameCommand) {
  healingTarget.value = undefined
  beforeAction.value = props.state
  emit('command', command)
}
</script>

<template>
  <div :class="['game-page', 'px-4 py-5 sm:px-8 sm:py-8']">
    <div :class="['game-layout', 'mx-auto max-w-7xl space-y-6']">
      <ResourceBar :state="state" />

      <header :class="['battle-heading', 'flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between']">
        <div>
          <p class="eyebrow">
            Contract encounter · Round {{ (encounter?.round ?? 0) + 1 }}
          </p>
          <h1 :class="['mt-2 text-4xl leading-tight sm:text-5xl']">
            {{ contract?.enemyName ?? 'The enemy' }}
          </h1>
          <p :class="['mt-2 text-base leading-relaxed', 'text-muted']">
            {{ contract?.name ?? 'Company contract' }}
          </p>
        </div>
        <div :class="['threat-card', 'rounded-2xl p-4 sm:min-w-64']" aria-live="polite" aria-atomic="true">
          <p class="eyebrow">
            Next threat
          </p>
          <p :class="['mt-1 text-lg font-semibold']">
            {{ nextThreatName }}
          </p>
          <p :class="['mt-1 text-sm', 'text-muted']">
            {{ contract?.enemyAttack ?? 0 }} damage if the enemy survives your action.
          </p>
        </div>
      </header>

      <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {{ combatStatus }}
      </p>

      <BattleScene :state="state" :before-action="beforeAction" :highlighted-crew="healingTarget" @command="perform" />

      <h2 id="battle-crew-title" class="sr-only">
        Choose an action
      </h2>
      <section :class="['special-actions', 'grid gap-4 md:grid-cols-2']" aria-label="Special actions">
        <article :class="['special-action-card', 'rounded-3xl p-5']">
          <div :class="['flex items-start justify-between gap-3']">
            <div>
              <p class="eyebrow">
                Mara · healer
              </p>
              <h2 :class="['mt-1 text-xl font-semibold']">
                Restore 4 health
              </h2>
            </div>
            <span class="charge-badge">{{ encounter?.healingCharges ?? 0 }} {{ encounter?.healingCharges === 1 ? 'use' : 'uses' }}</span>
          </div>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Save an injured crew member from the next hit. Mara must be active and alive.
          </p>
          <div v-if="healingTargets.length > 0 && healerCanAct && encounter?.healingCharges" :class="['mt-4 grid gap-2']">
            <Button
              v-for="target in healingTargets"
              :key="target.id"
              :class="['w-full']"
              color="green"
              variant="secondary"
              type="button"
              @focus="healingTarget = target.id"
              @blur="healingTarget = undefined"
              @mouseenter="healingTarget = target.id"
              @mouseleave="healingTarget = undefined"
              @click="perform({ type: 'heal', actor: 'healer', target: target.id })"
            >
              Heal {{ target.name }} · {{ target.health }} / {{ target.maxHealth }}
            </Button>
          </div>
          <p v-else :class="['action-unavailable', 'mt-4 rounded-xl px-3 py-2 text-sm']">
            {{ !healerCanAct
              ? 'Mara must be active and alive to heal.'
              : encounter?.healingCharges === 0
                ? 'Mara has used her heal.'
                : 'No injured crew member needs healing.' }}
          </p>
        </article>

        <article :class="['special-action-card', 'rounded-3xl p-5']">
          <div :class="['flex items-start justify-between gap-3']">
            <div>
              <p class="eyebrow">
                Grit · bomber
              </p>
              <h2 :class="['mt-1 text-xl font-semibold']">
                Throw the bomb
              </h2>
            </div>
            <span class="charge-badge">{{ encounter?.bombCharges ?? 0 }} {{ encounter?.bombCharges === 1 ? 'use' : 'uses' }}</span>
          </div>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Spend Grit’s one bomb for a powerful hit. The enemy still gets a turn if it survives.
          </p>
          <Button
            :class="['mt-4 w-full']"
            color="orange"
            variant="secondary"
            :disabled="!bomberCanAct || encounter?.bombCharges === 0"
            type="button"
            @click="perform({ type: 'bomb', actor: 'bomber' })"
          >
            Throw Grit’s bomb
          </Button>
          <p v-if="!bomberCanAct" :class="['mt-2 text-sm', 'text-muted']">
            Grit must be active and alive to throw it.
          </p>
          <p v-else-if="encounter?.bombCharges === 0" :class="['mt-2 text-sm', 'text-muted']">
            Grit has spent the bomb.
          </p>
        </article>
      </section>
    </div>
  </div>
</template>
