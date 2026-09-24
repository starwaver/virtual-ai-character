<script setup lang="ts">
import type { Component } from 'vue'

import type { GamePhase } from './game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import CompanyScreen from './components/company-screen.vue'
import EncounterScreen from './components/encounter-screen.vue'
import PreparationScreen from './components/preparation-screen.vue'
import ResultsScreen from './components/results-screen.vue'
import StartScreen from './components/start-screen.vue'

import { useCampaign } from './composables/use-campaign'

const campaign = useCampaign()

const screens: Record<GamePhase, Component> = {
  start: StartScreen,
  onboarding: StartScreen,
  company: CompanyScreen,
  preparation: PreparationScreen,
  encounter: EncounterScreen,
  results: ResultsScreen,
  terminal: ResultsScreen,
}

const activeScreen = computed(() => screens[campaign.state.value.phase])
</script>

<template>
  <div class="game-shell">
    <header class="game-header">
      <div class="game-brand">
        <p class="game-eyebrow">
          Brass Button Mercenary Company
        </p>
        <h1 class="game-title">
          Goblin Mercenary Company
        </h1>
      </div>
      <Button
        class="reset-button"
        color="amber"
        variant="secondary"
        shape="rounded"
        size="sm"
        type="button"
        @click="campaign.reset"
      >
        Reset company
      </Button>
    </header>

    <p v-if="campaign.persistenceError.value" class="save-error" role="alert" aria-live="polite">
      {{ campaign.persistenceError.value }}
    </p>

    <main class="game-content">
      <component
        :is="activeScreen"
        :state="campaign.state.value"
        @command="campaign.execute"
      />
    </main>
  </div>
</template>
