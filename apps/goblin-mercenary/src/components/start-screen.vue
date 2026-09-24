<script setup lang="ts">
import type { GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'

defineProps<{
  state: GameState
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()
</script>

<template>
  <div
    v-if="state.phase === 'start'"
    :class="[
      'start-screen',
      'px-4 py-8 sm:px-8 sm:py-12',
      'flex items-center justify-center',
    ]"
  >
    <section
      :class="[
        'start-card',
        'w-full max-w-5xl overflow-hidden rounded-3xl',
        'grid md:grid-cols-[1.2fr_0.8fr]',
      ]"
      aria-labelledby="start-title"
    >
      <div :class="['p-7 sm:p-12', 'flex flex-col justify-center gap-6']">
        <p :class="['eyebrow', 'flex items-center gap-2']">
          <span class="brass-dot" aria-hidden="true" />
          A small company with a big problem
        </p>
        <div class="space-y-4">
          <h1 id="start-title" :class="['start-title', 'text-4xl leading-tight sm:text-7xl sm:leading-none']">
            Brass Button
            <span :class="['block', 'start-title-accent']">Mercenary Company</span>
          </h1>
          <p :class="['start-lede', 'max-w-xl text-lg leading-relaxed sm:text-xl']">
            Lead a goblin crew, take risky contracts, and earn a name worth keeping.
          </p>
        </div>
        <div :class="['start-objective', 'rounded-2xl p-5 sm:p-6']">
          <p class="eyebrow">
            Captain’s objective
          </p>
          <p :class="['mt-2 text-xl font-semibold sm:text-2xl']">
            Complete all three contracts and bring the company home.
          </p>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Keep your crew alive, spend supplies with care, and finish every contract.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-4">
          <Button
            color="primary"
            variant="primary"
            size="lg"
            type="button"
            @click="emit('command', { type: 'begin-onboarding' })"
          >
            Start the company
          </Button>
          <p class="text-muted text-sm">
            No account or connection needed.
          </p>
        </div>
      </div>

      <aside :class="['start-side', 'p-7 sm:p-10', 'flex flex-col justify-between gap-8']">
        <div :class="['company-mark', 'mx-auto grid h-48 w-48 place-items-center rounded-full sm:h-60 sm:w-60']" aria-hidden="true">
          <div class="company-mark-inner grid h-36 w-36 place-items-center rounded-full sm:h-44 sm:w-44">
            <div class="company-mark-button grid h-16 w-16 place-items-center rounded-full text-3xl sm:h-20 sm:w-20">
              B
            </div>
          </div>
        </div>
        <blockquote :class="['nix-note', 'rounded-2xl p-5']">
          <p class="eyebrow">
            Nix, lieutenant and quartermaster
          </p>
          <p :class="['mt-3 text-lg font-medium leading-relaxed']">
            “Captain, I counted the gold twice. It is still barely enough.”
          </p>
        </blockquote>
      </aside>
    </section>
  </div>

  <div
    v-else
    :class="[
      'onboarding-screen',
      'px-4 py-8 sm:px-8 sm:py-12',
      'flex items-center justify-center',
    ]"
  >
    <section :class="['onboarding-card', 'w-full max-w-4xl rounded-3xl p-6 sm:p-10']" aria-labelledby="onboarding-title">
      <p class="eyebrow">
        Before you take the field
      </p>
      <h1 id="onboarding-title" :class="['mt-3 text-4xl leading-tight sm:text-5xl']">
        Captain, your company is yours to lead.
      </h1>
      <p :class="['mt-4 max-w-2xl text-lg leading-relaxed', 'text-muted']">
        Choose contracts, prepare two crew members, and guide them through a deterministic fight.
        Each choice changes who takes the next hit and how quickly the enemy falls.
      </p>

      <ol :class="['onboarding-steps', 'mt-8 grid gap-4 md:grid-cols-3']">
        <li :class="['onboarding-step', 'rounded-2xl p-5']">
          <span class="step-number">01</span>
          <h2 :class="['mt-3 text-xl font-semibold']">
            Pick a contract
          </h2>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Riskier work pays more. Read the threat and bring enough rations.
          </p>
        </li>
        <li :class="['onboarding-step', 'rounded-2xl p-5']">
          <span class="step-number">02</span>
          <h2 :class="['mt-3 text-xl font-semibold']">
            Choose two crew
          </h2>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Mog hits hard. Mara heals once. Grit can spend one bomb for a heavy hit.
          </p>
        </li>
        <li :class="['onboarding-step', 'rounded-2xl p-5']">
          <span class="step-number">03</span>
          <h2 :class="['mt-3 text-xl font-semibold']">
            Fight, then recover
          </h2>
          <p :class="['mt-2 text-sm leading-relaxed', 'text-muted']">
            Watch the next threat, claim your pay, and let the crew recover between contracts.
          </p>
        </li>
      </ol>

      <div :class="['onboarding-footer', 'mt-8 flex flex-col gap-4 rounded-2xl p-5 sm:flex-row sm:items-center sm:justify-between']">
        <p :class="['max-w-2xl text-sm leading-relaxed', 'text-muted']">
          Your run saves on this device. Reload the page to continue, or reset the company from the header.
        </p>
        <Button
          color="primary"
          variant="primary"
          size="lg"
          type="button"
          @click="emit('command', { type: 'complete-onboarding' })"
        >
          Go to the contract board
        </Button>
      </div>
    </section>
  </div>
</template>
