<script setup lang="ts">
import type { ContractId } from '../game'

defineProps<{
  location: ContractId
}>()
</script>

<template>
  <svg :class="['location-art', `location-${location}`]" viewBox="0 0 960 440" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
    <path fill="var(--sky)" d="M0 0H960V440H0Z" />
    <circle cx="710" cy="87" r="48" fill="#e5ca8c" opacity=".5" />
    <path d="M0 199L138 73L274 185L415 48L574 174L698 106L850 190L960 78V440H0Z" fill="var(--distant)" />
    <path d="M0 230Q194 165 335 223T646 195T960 222V440H0Z" fill="var(--middle)" />
    <path d="M0 316Q174 246 361 296T703 275T960 290V440H0Z" fill="var(--ground)" />
    <path d="M586 219Q401 262 589 325L828 440H277Q457 339 404 308T586 219Z" fill="#c8b884" opacity=".18" />
    <g v-if="location === 'moss-road'" stroke="#1e3831" stroke-width="7" stroke-linejoin="round">
      <path d="M65 305L95 87L114 309M842 283L875 50L899 294" fill="#3a5340" />
      <path d="M7 206L93 8L181 212ZM774 166L873 -34L972 185Z" fill="#29483a" />
      <path d="M-14 135L87 -30L169 144M794 99L870 -52L950 106" fill="#36543d" />
      <path d="M594 262L697 264L682 299L605 293Z" fill="#987447" />
      <circle cx="614" cy="301" r="14" fill="#434d36" />
      <circle cx="677" cy="303" r="14" fill="#434d36" />
      <path d="M614 262V241M644 261V225M674 264V244" stroke="#d3c99b" stroke-width="12" />
      <path d="M596 243Q609 212 634 242ZM620 227Q642 186 664 228ZM651 246Q676 214 695 249Z" fill="#bc7f55" />
    </g>
    <g v-else-if="location === 'bell-foundry'" stroke="#34312c" stroke-width="7" stroke-linejoin="round">
      <path d="M568 247V122L720 89L812 133V275Z" fill="#695a46" />
      <path d="M551 136L715 70L834 132L721 114Z" fill="#8a7051" />
      <path d="M747 99V27H782V117M595 114V58H623V101" fill="#5a5549" />
      <path d="M601 263V208Q632 164 663 208V266Z" fill="#e0a059" />
      <path d="M700 158H728V191H700ZM759 168H786V198H759Z" fill="#dbad66" />
      <path d="M716 46Q681 14 710 -20M767 10Q825 -5 786 -40" stroke="#ae9c76" stroke-width="24" opacity=".25" />
      <path d="M53 304L61 207H152L161 316M73 208V167H137V208" fill="#514c3e" />
    </g>
    <g v-else stroke="#282d33" stroke-width="7" stroke-linejoin="round">
      <path d="M578 273L590 122H635V95H673V126H719V90H753V120H807L824 292Z" fill="#565557" />
      <path d="M571 274L568 57L607 43L627 69L621 281M782 282L786 66L817 39L847 55L860 296" fill="#64605d" />
      <path d="M647 281V204Q688 143 739 211V286Z" fill="#282d33" />
      <path d="M614 100L699 105L694 178L651 161L612 172Z" fill="#8d5450" />
      <path d="M46 314L111 209L182 326M829 342L890 221L986 321" fill="#4d5553" />
    </g>
    <g fill="#d3c69a" opacity=".2">
      <path d="M42 365L84 353L105 366L68 372ZM794 370L838 360L861 373L816 380ZM327 279L344 271L361 280Z" />
      <circle cx="206" cy="216" r="3" /><circle cx="309" cy="129" r="2" /><circle cx="760" cy="310" r="3" />
    </g>
    <path d="M0 411L24 387L37 418L54 398L74 434L97 410L104 440H0ZM870 440L877 409L893 423L913 387L921 420L946 397L960 410V440Z" fill="#263b32" />
  </svg>
</template>

<style scoped>
.location-art {
  width: 100%;
  height: 100%;
  display: block;
  --sky: #879c87;
  --distant: #536f60;
  --middle: #405f4b;
  --ground: #59704d;
}
.location-bell-foundry {
  --sky: #b79c78;
  --distant: #887b63;
  --middle: #686951;
  --ground: #727052;
}
.location-black-pit {
  --sky: #9893a3;
  --distant: #696b7b;
  --middle: #515966;
  --ground: #5d665c;
}
</style>
