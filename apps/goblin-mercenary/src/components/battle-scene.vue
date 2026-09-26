<script setup lang="ts">
import type { CrewId, GameCommand, GameState } from '../game'

import { Button } from '@proj-airi/ui'
import { computed } from 'vue'

import CharacterArt from './character-art.vue'
import LocationArt from './location-art.vue'

import { getContracts, getNextThreatTarget } from '../game'

const props = defineProps<{
  state: GameState
  /** The pre-action snapshot supplies actual health changes, without replaying combat rules. */
  beforeAction?: GameState
  /** A heal button previews its target on focus or hover. This does not select a game action. */
  highlightedCrew?: CrewId
}>()

const emit = defineEmits<{
  command: [command: GameCommand]
}>()

const contract = computed(() => getContracts().find(item => item.id === props.state.selectedContract))
const threat = computed(() => props.state.phase === 'encounter' ? getNextThreatTarget(props.state) : null)
const crew = computed(() => props.state.activeCrew.map(id => props.state.crew[id]))
const latest = computed(() => props.state.history.at(-1))
const action = computed(() => {
  const command = latest.value?.command
  return command?.type === 'strike' || command?.type === 'heal' || command?.type === 'bomb' ? command : null
})
const enemyDefeated = computed(() => props.state.result?.outcome === 'victory' || props.state.encounter?.enemyHealth === 0)
const enemyChange = computed(() => (props.state.encounter?.enemyHealth ?? 0) - (props.beforeAction?.encounter?.enemyHealth ?? props.state.encounter?.enemyHealth ?? 0))
const actionSummary = computed(() => {
  const command = action.value
  if (!command) {
    return props.state.phase === 'encounter'
      ? 'The crew acts before the next threat'
      : props.state.result?.outcome === 'victory' ? 'The contract is complete.' : 'The crew has fallen back.'
  }
  const actor = props.state.crew[command.actor].name
  if (command.type === 'heal')
    return `${actor} · Heal ${props.state.crew[command.target].name}`
  return `${actor} · ${command.type === 'bomb' ? 'Bomb' : 'Strike'}`
})

function healthChange(id: CrewId) {
  if (!props.beforeAction)
    return 0
  return props.state.crew[id].health - props.beforeAction.crew[id].health
}
</script>

<template>
  <section v-if="contract" class="battle-scene" aria-label="Battlefield">
    <div class="battle-landscape">
      <LocationArt :location="contract.id" />
    </div>
    <div class="scene-heading">
      <span class="scene-location">{{ contract.name }}</span>
      <span class="scene-round">{{ state.phase === 'encounter' ? `Round ${(state.encounter?.round ?? 0) + 1}` : state.result?.outcome === 'victory' ? 'Victory' : 'Defeat' }}</span>
    </div>
    <div class="battle-stage">
      <div class="crew-formation">
        <article
          v-for="member in crew"
          :key="member.id"
          :class="['battle-unit', threat === member.id && 'battle-unit-threat', member.health === 0 && 'battle-unit-fallen', highlightedCrew === member.id && 'battle-unit-selected']"
          :aria-label="member.name"
        >
          <div class="unit-indicator">
            <span v-if="member.health === 0">Out of action</span>
            <span v-else-if="threat === member.id" class="threat-marker">↓ Next threat · {{ contract.enemyAttack }}</span>
            <span v-else>Ready</span>
          </div>
          <div :key="latest?.sequence" :class="['unit-figure', action?.actor === member.id && `unit-${action.type}`, healthChange(member.id) < 0 && 'unit-hit']">
            <CharacterArt :character="member.id" :fallen="member.health === 0" />
            <span v-if="healthChange(member.id) !== 0" :class="['health-change', healthChange(member.id) > 0 ? 'health-gained' : 'health-lost']">
              {{ healthChange(member.id) > 0 ? '+' : '' }}
              {{ healthChange(member.id) }}
            </span>
            <span v-if="action?.type === 'heal' && action.target === member.id" class="healing-effect" aria-hidden="true">+</span>
          </div>
          <div class="unit-caption">
            <h2>{{ member.name }}</h2>
            <div
              class="scene-health"
              role="meter"
              :aria-label="`${member.name} health`"
              :aria-valuenow="member.health"
              :aria-valuemin="0"
              :aria-valuemax="member.maxHealth"
            >
              <span :style="{ width: `${member.health / member.maxHealth * 100}%` }" />
            </div>
            <p>{{ member.health }} / {{ member.maxHealth }} health</p>
            <Button
              v-if="state.phase === 'encounter'"
              :class="['scene-strike', 'mt-2 w-full']"
              color="primary"
              variant="secondary"
              :disabled="member.health === 0"
              type="button"
              :aria-label="`Strike with ${member.name}`"
              @click="emit('command', { type: 'strike', actor: member.id })"
            >
              <span aria-hidden="true">↗</span> Strike
            </Button>
          </div>
        </article>
      </div>
      <div class="battle-versus" aria-hidden="true">
        ×
      </div>
      <article :class="['battle-unit', 'battle-enemy']" :aria-label="contract.enemyName">
        <div class="unit-indicator">
          <span>{{ enemyDefeated ? 'Defeated' : `${contract.enemyAttack} damage / turn` }}</span>
        </div>
        <div :key="latest?.sequence" :class="['unit-figure', enemyChange < 0 && 'unit-hit']">
          <CharacterArt :character="contract.id" :fallen="enemyDefeated" />
          <span v-if="enemyChange < 0" class="health-change health-lost">{{ enemyChange }}</span>
          <span v-if="action?.type === 'bomb'" class="bomb-effect" aria-hidden="true">✹</span>
          <span v-else-if="action?.type === 'strike'" class="strike-effect" aria-hidden="true" />
        </div>
        <div class="unit-caption">
          <h2>{{ contract.enemyName }}</h2>
          <div
            class="scene-health enemy-scene-health"
            role="meter"
            :aria-label="`${contract.enemyName} health`"
            :aria-valuenow="state.encounter?.enemyHealth ?? 0"
            :aria-valuemin="0"
            :aria-valuemax="contract.enemyHealth"
          >
            <span :style="{ width: `${(state.encounter?.enemyHealth ?? 0) / contract.enemyHealth * 100}%` }" />
          </div>
          <p>{{ state.encounter?.enemyHealth ?? 0 }} / {{ contract.enemyHealth }} health</p>
        </div>
      </article>
    </div>
    <div class="scene-caption" role="status" aria-live="polite" aria-atomic="true">
      <p :key="latest?.sequence" class="action-summary">
        {{ actionSummary }}
        <span v-if="enemyChange < 0"> · {{ -enemyChange }} damage</span>
      </p>
      <p v-if="threat">
        {{ state.crew[threat].name }}
        faces {{ contract.enemyAttack }}
        damage if the enemy survives.
      </p>
    </div>
  </section>
</template>

<style scoped>
.battle-scene {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border: 1px solid #819377;
  border-radius: 1.5rem;
  background: #354c3e;
  box-shadow: 0 16px 50px #0004;
}
.battle-landscape { position: absolute; inset: 0; z-index: -2; }
.battle-landscape::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #172b2420 20%, #172b2410 40%, #172b24d9 87%);
}
.scene-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
}
.scene-location, .scene-round {
  padding: .4rem .8rem;
  border: 1px solid #e3cf9366;
  border-radius: 2rem;
  background: #1b2b26ed;
  color: #f0db9f;
  font-size: .75rem;
  font-weight: 700;
}
.battle-stage {
  display: grid;
  grid-template-columns: 1.6fr .3fr 1fr;
  align-items: end;
  gap: 1rem;
  padding: 1rem 5% 1.5rem;
}
.crew-formation {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  align-items: end;
}
.battle-unit { min-width: 0; text-align: center; }
.unit-indicator {
  height: 2.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.unit-indicator span {
  background: #20392eed;
  border: 1px solid #b5c89a70;
  color: #e2e9c8;
  border-radius: 2rem;
  padding: .25rem .65rem;
  font-size: .7rem;
  font-weight: 700;
}
.unit-indicator .threat-marker {
  background: #71392a;
  color: #ffe2ab;
  border-color: #efb975;
}
.unit-figure {
  position: relative;
  width: min(100%, 210px);
  margin: auto;
  transform-origin: 50% 85%;
}
.battle-enemy .unit-figure { width: min(100%, 250px); }
.battle-unit-selected .unit-caption {
  outline: 3px solid #d0edac;
  outline-offset: 3px;
  background: #385840;
}
.battle-unit-threat .unit-figure::after {
  content: '';
  position: absolute;
  bottom: 2%;
  left: 13%;
  width: 74%;
  height: 10%;
  border: 3px solid #f2be73;
  border-radius: 50%;
  box-shadow: 0 0 18px #e48d5055;
}
.unit-caption {
  max-width: 250px;
  margin: auto;
  padding: .65rem .8rem;
  border: 1px solid #d7cd9f40;
  border-radius: .85rem;
  background: #172b25ed;
}
.unit-caption h2 {
  min-height: 2.5em;
  display: grid;
  align-content: center;
  font-size: .85rem;
  line-height: 1.25;
  font-weight: 700;
  color: #f4e6c7;
}
.unit-caption p {
  margin-top: .35rem;
  font-size: .7rem;
  color: #d5dabc;
}
.scene-health {
  height: .5rem;
  overflow: hidden;
  border-radius: 1rem;
  background: #0d1c17;
  margin-top: .5rem;
}
.scene-health span {
  display: block;
  height: 100%;
  background: #b4d282;
  transition: width 220ms ease;
}
.enemy-scene-health span { background: #e29a72; }
.battle-versus {
  align-self: center;
  color: #f5dfae;
  text-align: center;
  font-family: Georgia, serif;
  font-size: 2.8rem;
  text-shadow: 0 2px 10px #172b24;
}
.scene-caption {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: .5rem 1.5rem;
  background: #15271feb;
  padding: .9rem 1.5rem;
  font-size: .8rem;
  color: #c5cfb5;
  border-top: 1px solid #b6c58a33;
}
.action-summary { color: #f3d291; font-weight: 600; }
.health-change {
  position: absolute;
  top: 12%;
  right: 0;
  min-width: 2.5rem;
  padding: .3rem;
  border: 2px solid currentColor;
  border-radius: .6rem;
  background: #172b25;
  font-size: 1.4rem;
  font-weight: 800;
  animation: health-pop 550ms ease-out;
  z-index: 3;
}
.health-lost { color: #ffd0a4; }
.health-gained { color: #d0f5ae; }
.healing-effect {
  position: absolute;
  top: 30%;
  left: 35%;
  color: #e2ffc5;
  font-size: 4rem;
  animation: heal-glow 700ms both;
}
.bomb-effect {
  position: absolute;
  inset: 5%;
  display: grid;
  place-items: center;
  font-size: 9rem;
  color: #ffd897;
  animation: bomb-burst 600ms both;
}
.strike-effect {
  position: absolute;
  top: 32%;
  left: 20%;
  width: 65%;
  height: 9px;
  border-radius: 100%;
  background: #fff1c8;
  transform: rotate(-40deg);
  animation: heal-glow 500ms both;
}
.unit-strike { animation: strike-lunge 350ms ease; }
.unit-bomb { animation: strike-lunge 350ms ease; }
.unit-hit { animation: impact 400ms ease; }
@keyframes strike-lunge {
  40% {
    transform: translate(16px, -8px) rotate(7deg);
  }
}
@keyframes impact {
  35% {
    transform: translateX(10px) rotate(5deg);
  }
}
@keyframes health-pop {
  from {
    opacity: 0;
    transform: translateY(12px) scale(.7);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
@keyframes heal-glow {
  0% {
    opacity: 0;
    scale: .5;
  }
  35% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    scale: 1.4;
  }
}
@keyframes bomb-burst {
  0% {
    opacity: 0;
    transform: scale(.2) rotate(-30deg);
  }
  30% {
    opacity: .95;
  }
  100% {
    opacity: 0;
    transform: scale(1.3) rotate(20deg);
  }
}
@media (max-width: 600px) {
  .scene-heading { padding: .7rem; gap: .5rem; }
.scene-location, .scene-round {
  font-size: .65rem;
  padding: .3rem .5rem;
}
.battle-stage {
  grid-template-columns: 1.65fr 1fr;
  gap: .6rem;
  padding: .5rem .6rem 1rem;
}
  .crew-formation { gap: .4rem; }
  .battle-versus { display: none; }
  .unit-caption { padding: .4rem; }
  .unit-caption h2 { font-size: .7rem; min-height: 3.75em; }
  .unit-caption p { font-size: .62rem; }
  .unit-indicator { height: 2.5rem; }
.unit-indicator span {
  font-size: .58rem;
  padding: .2rem .3rem;
}
  .battle-enemy { padding-bottom: 2.8rem; }
  .scene-caption { padding: .8rem; font-size: .72rem; }
.health-change {
  font-size: 1rem;
  min-width: 1.6rem;
  padding: .1rem;
}
}
@media (prefers-reduced-motion: reduce) {
.unit-figure, .health-change, .healing-effect, .bomb-effect, .strike-effect {
  animation: none;
}
.healing-effect, .bomb-effect, .strike-effect {
  display: none;
}
  .scene-health span { transition: none; }
}
</style>
