<script setup lang="ts">
import type { ContractRisk, GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import ResourceBar from './resource-bar.vue'
import RosterList from './roster-list.vue'

import { CONTRACT_IDS, getContracts } from '../game'

const props = defineProps<{
  state: GameState
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()

const contracts = computed(() => getContracts().map(contract => ({
  ...contract,
  completed: props.state.completedContracts.includes(contract.id),
})))

const riskLabels: Record<ContractRisk, string> = {
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
}

const campaignProgress = computed(() => `${props.state.completedContracts.length} / ${CONTRACT_IDS.length}`)
</script>

<template>
  <div :class="['game-page', 'px-4 py-5 sm:px-8 sm:py-8']">
    <div :class="['game-layout', 'mx-auto max-w-7xl space-y-6']">
      <ResourceBar :state="state" />

      <header :class="['page-heading', 'flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between']">
        <div>
          <p class="eyebrow">
            Brass Button Mercenary Company
          </p>
          <h1 :class="['mt-2 text-4xl leading-tight sm:text-5xl']">
            Contract board
          </h1>
          <p :class="['mt-2 max-w-2xl text-base leading-relaxed', 'text-muted']">
            Choose your next job, then prepare a crew of two. Nix keeps the books and watches your back.
          </p>
        </div>
        <div :class="['progress-card', 'rounded-2xl px-5 py-4']" aria-label="Campaign progress">
          <p class="eyebrow">
            Campaign
          </p>
          <p :class="['mt-1 text-2xl font-semibold']">
            {{ campaignProgress }} contracts
          </p>
          <div
            :class="['progress-track', 'mt-3 h-2 overflow-hidden rounded-full']"
            role="progressbar"
            :aria-valuenow="state.completedContracts.length"
            :aria-valuemin="0"
            :aria-valuemax="CONTRACT_IDS.length"
            :aria-valuetext="`${campaignProgress} contracts complete`"
            aria-label="Contracts completed"
          >
            <div
              class="progress-fill h-full rounded-full"
              :style="{ width: `${(state.completedContracts.length / CONTRACT_IDS.length) * 100}%` }"
            />
          </div>
        </div>
      </header>

      <div :class="['company-grid', 'grid gap-6 xl:grid-cols-[1.6fr_0.8fr]']">
        <section :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="contracts-title">
          <div :class="['section-heading', 'mb-5 flex items-end justify-between gap-4']">
            <div>
              <p class="eyebrow">
                Choose a job
              </p>
              <h2 id="contracts-title" :class="['mt-1 text-2xl font-semibold sm:text-3xl']">
                Available contracts
              </h2>
            </div>
            <span class="small-label">Earn gold, rations, and reputation</span>
          </div>
          <div :class="['contract-grid', 'grid gap-4 md:grid-cols-2 2xl:grid-cols-3']">
            <article
              v-for="contract in contracts"
              :key="contract.id"
              :class="[
                'contract-card',
                'flex flex-col rounded-2xl p-5',
                contract.completed && 'contract-card-complete',
              ]"
            >
              <div :class="['flex items-start justify-between gap-3']">
                <span :class="['risk-badge', `risk-${contract.risk}`]">
                  {{ riskLabels[contract.risk] }}
                </span>
                <span v-if="contract.completed" class="completed-label">Complete</span>
                <span v-else class="contract-cost">{{ contract.rationCost }} ration</span>
              </div>
              <h3 :class="['mt-4 text-xl font-semibold leading-snug']">
                {{ contract.name }}
              </h3>
              <p :class="['mt-2 min-h-12 text-sm leading-relaxed', 'text-muted']">
                {{ contract.description }}
              </p>
              <div :class="['enemy-note', 'mt-4 rounded-xl px-4 py-3']">
                <span class="small-label">Expected threat</span>
                <p :class="['mt-1 font-semibold']">
                  {{ contract.enemyName }}
                </p>
                <p :class="['mt-2 text-xs leading-relaxed', 'text-muted']">
                  {{ contract.enemyHealth }} health · {{ contract.enemyAttack }} damage per turn
                </p>
              </div>
              <ul :class="['mt-4 flex flex-wrap gap-2']" aria-label="Contract rewards">
                <li class="reward-chip">
                  +{{ contract.rewards.coin }} gold
                </li>
                <li class="reward-chip">
                  +{{ contract.rewards.rations }} rations
                </li>
                <li class="reward-chip">
                  +{{ contract.rewards.reputation }} reputation
                </li>
              </ul>
              <div :class="['preparation-tip', 'mt-4 flex-1 rounded-xl px-4 py-3']">
                <span class="small-label">Nix recommends</span>
                <p :class="['mt-1 text-sm leading-relaxed']">
                  {{ contract.recommendedPreparation }}
                </p>
              </div>
              <Button
                :class="['mt-5 w-full justify-between']"
                :disabled="contract.completed"
                :color="contract.completed ? 'neutral' : 'primary'"
                :variant="contract.completed ? 'secondary' : 'primary'"
                type="button"
                @click="emit('command', { type: 'select-contract', contractId: contract.id })"
              >
                <span>{{ contract.completed ? 'Contract complete' : 'Prepare this contract' }}</span>
                <span aria-hidden="true">→</span>
              </Button>
            </article>
          </div>
        </section>

        <aside :class="['section-card', 'rounded-3xl p-5 sm:p-7']" aria-labelledby="roster-title">
          <p class="eyebrow">
            Company roster
          </p>
          <h2 id="roster-title" :class="['mt-1 text-2xl font-semibold']">
            Your crew
          </h2>
          <p :class="['mt-2 mb-5 text-sm leading-relaxed', 'text-muted']">
            Health carries between jobs. Each survivor recovers a little after a successful contract.
          </p>
          <RosterList :state="state" />
        </aside>
      </div>
    </div>
  </div>
</template>
