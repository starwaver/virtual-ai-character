<script setup lang="ts">
import type { GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import BattleScene from './battle-scene.vue'
import ResourceBar from './resource-bar.vue'
import RosterList from './roster-list.vue'

import { CONTRACT_IDS, getContracts } from '../game'

const props = defineProps<{
  state: GameState
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()

const result = computed(() => props.state.result)
const contract = computed(() => getContracts().find(item => item.id === result.value?.contractId) ?? null)
const isTerminal = computed(() => props.state.phase === 'terminal')
const isVictory = computed(() => result.value?.outcome === 'victory')
const isCampaignWon = computed(() => props.state.status === 'won')
const isCampaignLost = computed(() => props.state.status === 'lost')
const canClaimReward = computed(() => props.state.phase === 'results' && isVictory.value && result.value?.rewardApplied === false)
const canContinue = computed(() => {
  const current = result.value
  return props.state.phase === 'results'
    && current !== null
    && (current.outcome === 'defeat' || (current.outcome === 'victory' && current.rewardApplied))
})
const rewardCount = computed(() => `${props.state.completedContracts.length} / ${CONTRACT_IDS.length}`)
const roundCount = computed(() => result.value?.rounds ?? 0)
const roundLabel = computed(() => `${roundCount.value} ${roundCount.value === 1 ? 'round' : 'rounds'}`)
const injuredCrew = computed(() => Object.values(props.state.crew).filter(member => member.health < member.maxHealth))

const outcomeGuidance = computed(() => {
  if (isCampaignWon.value)
    return 'Every contract is complete. Your final pay is in the ledger. Start a new company when you are ready.'
  if (isCampaignLost.value)
    return 'This run is over. Start a new company with a fresh roster when you are ready.'
  if (isVictory.value)
    return 'Claim the contract pay, then return to the board. The crew recovers 2 health between successful contracts.'

  return 'The crew keeps its injuries. End this run, then start a new company with a fresh roster.'
})

const resultStatus = computed(() => {
  if (isCampaignWon.value)
    return 'Campaign complete. The Brass Button Company earned the town’s trust.'
  if (isCampaignLost.value)
    return 'Campaign over. The company must rebuild before taking another job.'
  if (isVictory.value && result.value?.rewardApplied)
    return 'Victory. Contract pay is on the ledger. The crew recovers when you continue.'
  if (isVictory.value)
    return `Victory. The enemy fell after ${roundLabel.value}.`
  return 'Defeat. The crew could not hold the line.'
})
</script>

<template>
  <div :class="['game-page', 'px-4 py-5 sm:px-8 sm:py-8']">
    <div :class="['game-layout', 'mx-auto max-w-7xl space-y-6']">
      <ResourceBar :state="state" />

      <section
        :class="[
          'results-hero',
          'rounded-3xl p-6 sm:p-9',
          isCampaignWon ? 'results-hero-won' : isVictory ? 'results-hero-victory' : 'results-hero-defeat',
        ]"
        aria-labelledby="results-title"
        aria-live="polite"
        aria-atomic="true"
      >
        <p class="eyebrow">
          {{ isTerminal ? 'Campaign end' : 'After the encounter' }}
        </p>
        <h1 id="results-title" :class="['mt-2 text-4xl leading-tight sm:text-5xl']">
          {{ isCampaignWon ? 'Brass Button stands tall.' : isCampaignLost ? 'The company needs a new start.' : isVictory ? 'The contract is complete.' : 'The crew has fallen back.' }}
        </h1>
        <p :class="['mt-3 max-w-3xl text-base leading-relaxed', 'text-muted']">
          {{ resultStatus }}
        </p>
        <p v-if="contract" :class="['mt-2 text-sm', 'text-muted']">
          {{ contract.name }} · {{ roundLabel }}
        </p>
      </section>

      <BattleScene v-if="isVictory" :state="state" />

      <div :class="['results-grid', 'grid gap-6 xl:grid-cols-[1.1fr_0.9fr]']">
        <section :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="outcome-title">
          <p class="eyebrow">
            {{ isVictory ? 'Company pay' : 'The cost' }}
          </p>
          <h2 id="outcome-title" :class="['mt-1 text-2xl font-semibold']">
            {{ isVictory ? 'Reward and recovery' : 'Injuries and next steps' }}
          </h2>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            {{ outcomeGuidance }}
          </p>

          <dl v-if="isVictory && result" :class="[result.rewardApplied && 'reward-claimed', 'reward-summary', 'mt-5 grid grid-cols-3 gap-3']" aria-label="Contract rewards">
            <div class="reward-summary-item">
              <dt class="small-label">
                Gold
              </dt>
              <dd><strong>+{{ result.rewards.coin }}</strong></dd>
            </div>
            <div class="reward-summary-item">
              <dt class="small-label">
                Rations
              </dt>
              <dd><strong>+{{ result.rewards.rations }}</strong></dd>
            </div>
            <div class="reward-summary-item">
              <dt class="small-label">
                Reputation
              </dt>
              <dd><strong>+{{ result.rewards.reputation }}</strong></dd>
            </div>
          </dl>

          <div v-if="injuredCrew.length > 0" :class="['injury-list', 'mt-5 rounded-2xl p-4']">
            <p class="eyebrow">
              Crew that needs care
            </p>
            <ul :class="['mt-3 grid gap-2 sm:grid-cols-2']">
              <li v-for="member in injuredCrew" :key="member.id" class="injury-row">
                <span>{{ member.name }}</span>
                <span>{{ member.health }} / {{ member.maxHealth }} health</span>
              </li>
            </ul>
          </div>

          <div v-if="canClaimReward || canContinue" :class="['mt-6 flex flex-col gap-3 sm:flex-row']">
            <Button
              v-if="canClaimReward"
              color="primary"
              variant="primary"
              size="lg"
              type="button"
              @click="emit('command', { type: 'claim-reward' })"
            >
              Claim the contract pay
            </Button>
            <Button
              v-if="canContinue"
              color="primary"
              variant="primary"
              size="lg"
              type="button"
              @click="emit('command', { type: 'continue-campaign' })"
            >
              {{ isVictory ? 'Continue to the company' : 'End this campaign' }}
            </Button>
          </div>

          <div v-if="isTerminal" :class="['terminal-card', 'mt-6 rounded-2xl p-5']">
            <p class="eyebrow">
              Campaign progress
            </p>
            <p :class="['mt-1 text-xl font-semibold']">
              {{ rewardCount }} contracts complete
            </p>
            <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
              {{ isCampaignWon
                ? 'You completed every contract and kept the company together. Start another run whenever you are ready.'
                : 'A failed run is not the end of the company. Nix has already started a new ledger.' }}
            </p>
            <Button
              :class="['mt-5']"
              color="primary"
              variant="secondary"
              type="button"
              @click="emit('command', { type: 'restart-campaign' })"
            >
              Start a new company
            </Button>
          </div>
        </section>

        <aside :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="results-roster-title">
          <p class="eyebrow">
            Current company roster
          </p>
          <h2 id="results-roster-title" :class="['mt-1 text-2xl font-semibold']">
            Where everyone stands
          </h2>
          <p :class="['mt-2 mb-5 text-sm leading-relaxed', 'text-muted']">
            {{ isTerminal && isCampaignWon
              ? 'Your crew made it through the full campaign.'
              : 'Review each crew member’s health before you choose the next step.' }}
          </p>
          <RosterList :state="state" />
        </aside>
      </div>
    </div>
  </div>
</template>
