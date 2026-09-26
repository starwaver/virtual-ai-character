<script setup lang="ts">
import type { CrewId, GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

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
const healthyCrew = computed(() => props.state.activeCrew.filter(id => props.state.crew[id].health > 0).map(id => props.state.crew[id]))
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

function healthPercent(id: CrewId): number {
  const member = props.state.crew[id]
  return (member.health / member.maxHealth) * 100
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

      <section :class="['battle-grid', 'grid gap-6 xl:grid-cols-[0.8fr_1.2fr]']" aria-label="Battle">
        <div :class="['enemy-panel', 'rounded-3xl p-6 sm:p-8']">
          <div :class="['enemy-art', 'mx-auto grid h-48 w-48 place-items-center rounded-full sm:h-56 sm:w-56']" aria-hidden="true">
            <div :class="['enemy-art-core', 'grid h-32 w-32 place-items-center rounded-full text-6xl sm:h-40 sm:w-40']">
              ⚔
            </div>
          </div>
          <div :class="['mt-6 text-center']">
            <p class="eyebrow">
              Enemy strength
            </p>
            <p :class="['mt-1 text-3xl font-semibold']">
              {{ encounter?.enemyHealth ?? 0 }}
              <span :class="['text-lg font-normal', 'text-muted']">/ {{ encounter?.enemyMaxHealth ?? 0 }} health</span>
            </p>
            <div
              :class="['enemy-health-track', 'mt-4 h-3 overflow-hidden rounded-full']"
              role="meter"
              :aria-valuenow="encounter?.enemyHealth ?? 0"
              :aria-valuemin="0"
              :aria-valuemax="encounter?.enemyMaxHealth ?? 0"
              :aria-valuetext="`${encounter?.enemyHealth ?? 0} of ${encounter?.enemyMaxHealth ?? 0} health`"
              :aria-label="`${contract?.enemyName ?? 'Enemy'} health`"
            >
              <div
                class="enemy-health-fill h-full rounded-full transition-all duration-300"
                :style="{ width: `${((encounter?.enemyHealth ?? 0) / Math.max(encounter?.enemyMaxHealth ?? 1, 1)) * 100}%` }"
              />
            </div>
          </div>
          <div :class="['battle-tip', 'mt-6 rounded-2xl p-4']">
            <p class="eyebrow">
              Nix calls the rhythm
            </p>
            <p :class="['mt-2 text-sm leading-relaxed']">
              “Captain, they swing at {{ nextThreatName }} next. Finish the job or make sure {{ nextThreatName }} can take it.”
            </p>
          </div>
        </div>

        <div :class="['flex flex-col gap-6']">
          <section :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="battle-crew-title">
            <div :class="['flex items-end justify-between gap-4']">
              <div>
                <p class="eyebrow">
                  Your decision
                </p>
                <h2 id="battle-crew-title" :class="['mt-1 text-2xl font-semibold']">
                  Choose an action
                </h2>
              </div>
              <span class="small-label">The crew acts before the next threat</span>
            </div>
            <div :class="['combat-crew', 'mt-5 grid gap-3 sm:grid-cols-2']">
              <article
                v-for="member in healthyCrew"
                :key="member.id"
                :class="['combat-member', 'rounded-2xl p-4']"
              >
                <div :class="['flex items-start justify-between gap-3']">
                  <div>
                    <h3 :class="['font-semibold']">
                      {{ member.name }}
                    </h3>
                    <p :class="['mt-1 text-xs capitalize', 'text-muted']">
                      {{ member.roles.join(' · ') }}
                    </p>
                  </div>
                  <span class="health-value">{{ member.health }} / {{ member.maxHealth }}</span>
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
                  <div
                    class="crew-health-fill h-full rounded-full"
                    :style="{ width: `${healthPercent(member.id)}%` }"
                  />
                </div>
                <Button
                  :class="['mt-4 w-full']"
                  color="primary"
                  variant="secondary"
                  type="button"
                  @click="emit('command', { type: 'strike', actor: member.id })"
                >
                  Strike with {{ member.name }}
                </Button>
              </article>
            </div>
          </section>

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
                  @click="emit('command', { type: 'heal', actor: 'healer', target: target.id })"
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
                @click="emit('command', { type: 'bomb', actor: 'bomber' })"
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
      </section>
    </div>
  </div>
</template>
