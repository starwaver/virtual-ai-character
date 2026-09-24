<script setup lang="ts">
import type { GameState } from '../game'

import { computed } from 'vue'

import { CONTRACT_IDS } from '../game'

const props = defineProps<{
  state: GameState
}>()

const progress = computed(() => `${props.state.completedContracts.length} / ${CONTRACT_IDS.length}`)
</script>

<template>
  <section :class="['resource-bar', 'grid gap-3 sm:grid-cols-2 xl:grid-cols-4']" aria-label="Company status">
    <div :class="['resource-brand', 'rounded-2xl p-4 sm:px-5']">
      <p class="eyebrow">
        Brass Button Mercenary Company
      </p>
      <p :class="['mt-1 text-lg font-semibold']">
        Captain’s field ledger
      </p>
    </div>
    <div :class="['resource-item', 'rounded-2xl p-4 sm:px-5']">
      <span class="resource-symbol" aria-hidden="true">◈</span>
      <div>
        <p class="small-label">
          Company gold
        </p>
        <p :class="['mt-1 text-xl font-semibold']">
          {{ state.resources.coin }}
        </p>
      </div>
    </div>
    <div :class="['resource-item', 'rounded-2xl p-4 sm:px-5']">
      <span class="resource-symbol" aria-hidden="true">✦</span>
      <div>
        <p class="small-label">
          Rations
        </p>
        <p :class="['mt-1 text-xl font-semibold']">
          {{ state.resources.rations }}
        </p>
      </div>
    </div>
    <div :class="['resource-item', 'rounded-2xl p-4 sm:px-5']">
      <span class="resource-symbol" aria-hidden="true">★</span>
      <div>
        <p class="small-label">
          Reputation · contracts
        </p>
        <p :class="['mt-1 text-xl font-semibold']">
          {{ state.resources.reputation }} · {{ progress }}
        </p>
      </div>
    </div>
  </section>
</template>
