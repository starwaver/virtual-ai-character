<script setup lang="ts">
import type { ContractId, CrewId } from '../game'

withDefaults(defineProps<{
  character: CrewId | ContractId
  fallen?: boolean
}>(), {
  fallen: false,
})
</script>

<template>
  <svg
    :class="['character-art', `character-${character}`, fallen && 'character-fallen']"
    viewBox="0 0 200 220"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <ellipse cx="100" cy="204" rx="65" ry="11" fill="#111d1c" opacity=".45" />
    <g class="character-body" stroke="#182925" stroke-width="4" stroke-linejoin="round" stroke-linecap="round">
      <path d="M64 161L58 196L84 197L95 163M110 162L117 198L143 197L134 157" fill="#493d32" />
      <path d="M54 195L84 195L85 207H49ZM116 195H144L151 207H115Z" fill="#26312b" />
      <path d="M64 102Q100 84 136 105L145 169Q101 188 53 167Z" class="character-coat" />
      <path d="M70 113L53 133L43 159L28 150L40 112L64 99M134 106L155 123L167 151L151 160L133 130" class="character-skin" />
      <path d="M61 148L141 150L142 162L58 160Z" fill="#493d32" />
      <rect x="91" y="147" width="20" height="18" rx="3" fill="#e9be69" />
      <path d="M52 54L16 39L32 80L59 86M146 54L183 37L170 80L143 86" class="character-skin" />
      <path d="M44 63L28 54L37 74M156 64L171 52L164 74" stroke="#57765b" />
      <path d="M53 52Q56 20 98 22Q142 21 148 53L143 96Q121 120 97 117Q67 115 54 95Z" class="character-skin" />
      <path d="M62 64L86 67M113 67L137 60" stroke-width="6" />
      <path d="M65 73Q76 69 86 74L83 85H69ZM113 74Q125 67 135 72L132 83H117Z" fill="#f3e5af" stroke-width="2" />
      <path d="M78 74V82M123 72V80" stroke-width="5" />
      <path d="M95 74L86 93L108 94" class="character-skin" />
      <path d="M79 103Q99 109 121 100" />
      <path d="M79 102L82 92L88 105M111 104L118 92L120 101" fill="#f6ebc9" stroke-width="2" />
      <template v-if="character === 'captain'">
        <path d="M48 49L62 18L94 31L129 17L151 45Q103 34 48 49Z" fill="#bd8343" />
        <path d="M69 112L110 146M64 128L83 111" stroke="#e8c37a" stroke-width="8" />
        <path d="M154 150L173 81L181 63L187 82L166 155Z" fill="#c6d8c4" />
        <path d="M151 145L176 153" stroke="#d6ae58" stroke-width="7" />
      </template>
      <template v-else-if="character === 'nix'">
        <path d="M49 50Q62 8 111 20L147 44Z" fill="#b49b69" />
        <path d="M126 29L143 8L146 40" fill="#e8d6a3" />
        <rect x="129" y="122" width="42" height="52" rx="4" fill="#b08249" transform="rotate(12 129 122)" />
        <path d="M137 135L157 139M135 146L153 150" stroke="#eadca9" />
        <circle cx="77" cy="77" r="14" stroke="#d9b567" stroke-width="3" />
      </template>
      <template v-else-if="character === 'mog'">
        <path d="M48 56Q47 14 98 14Q148 15 152 53L126 46L99 38L73 50Z" fill="#879a8b" />
        <path d="M99 15V43" stroke="#c4d0b4" stroke-width="8" />
        <path d="M131 116L172 112L179 155Q162 182 142 173Z" fill="#748776" />
        <path d="M153 122L161 160M141 141L173 137" stroke="#d9ba6e" stroke-width="5" />
        <path d="M36 150L26 94M14 97L39 93L39 77L10 82Z" fill="#9da99b" />
      </template>
      <template v-else-if="character === 'healer'">
        <path d="M48 55Q48 10 98 10Q148 10 153 56L130 41L102 25L74 42Z" fill="#dddbc1" />
        <path d="M90 22H107M98 15V32" stroke="#527c65" stroke-width="5" />
        <path d="M158 173L165 58" stroke="#b49762" stroke-width="8" />
        <path d="M165 55C136 49 143 26 155 32C159 10 185 17 181 38Q187 52 165 55Z" fill="#a8d8a0" />
        <path d="M89 126H110M100 116V137" stroke="#e4e4c2" stroke-width="7" />
      </template>
      <template v-else-if="character === 'bomber'">
        <path d="M51 54Q45 15 101 17Q141 19 150 51Z" fill="#a77646" />
        <path d="M51 45L148 42" stroke="#493d32" stroke-width="9" />
        <rect x="65" y="32" width="25" height="24" rx="7" fill="#dfb675" />
        <rect x="109" y="31" width="25" height="24" rx="7" fill="#dfb675" />
        <path d="M90 42H109" stroke="#d9ba6e" />
        <circle cx="159" cy="146" r="24" fill="#354443" />
        <path d="M161 122Q178 117 170 103" stroke="#e5c790" />
        <path d="M166 97L177 103M171 93L173 107" stroke="#f3ad59" />
      </template>
      <template v-else-if="character === 'moss-road'">
        <path d="M47 51Q61 5 103 17Q138 19 153 53L123 43L88 49Z" fill="#9b6549" />
        <path d="M119 69L136 62L138 81L118 85Z" fill="#2e3530" />
        <path d="M32 153L32 101L19 91L22 66L43 66L46 91L37 104" fill="#899b88" />
      </template>
      <template v-else-if="character === 'bell-foundry'">
        <path d="M47 57L51 25L78 12H122L145 28L153 56Z" fill="#837d70" />
        <path d="M47 43L152 42M74 16L72 40M123 17L126 41" stroke="#b6aa85" />
        <path d="M151 162L156 79" stroke="#987851" stroke-width="10" />
        <path d="M129 61L181 65L177 96L128 90Z" fill="#86877a" />
        <path d="M63 114L135 115L123 150H75Z" fill="#837d70" />
      </template>
      <template v-else>
        <path d="M46 56L52 23L72 34L86 9L105 30L129 13L134 37L150 28L151 57Z" fill="#9b7154" />
        <path d="M53 112L38 102L48 88L74 112M130 109L154 88L167 105L148 120" fill="#c7bc98" />
        <path d="M155 163L165 55" stroke="#bba071" stroke-width="8" />
        <path d="M165 59L175 25L184 67L167 91L148 69Z" fill="#9aada4" />
        <path d="M79 122L104 149L123 120" stroke="#be9563" stroke-width="7" />
      </template>
    </g>
  </svg>
</template>

<style scoped>
.character-art {
  width: 100%;
  height: auto;
  overflow: visible;
  --skin: #9bb86a;
  --coat: #987348;
}
.character-skin { fill: var(--skin); }
.character-coat { fill: var(--coat); }
.character-nix { --skin: #a9bd7b; --coat: #887c57; }
.character-mog { --skin: #7e9c62; --coat: #6c8072; }
.character-healer { --skin: #a8c789; --coat: #517e72; }
.character-bomber { --skin: #b1bc72; --coat: #a26840; }
.character-moss-road { --skin: #94a96d; --coat: #805541; }
.character-bell-foundry { --skin: #ad9d72; --coat: #705b49; }
.character-black-pit { --skin: #899a88; --coat: #685568; }
.character-fallen { filter: grayscale(.85); opacity: .6; }
.character-fallen .character-body {
  transform: translate(12px, 34px) rotate(-16deg);
  transform-origin: 100px 180px;
}
</style>
