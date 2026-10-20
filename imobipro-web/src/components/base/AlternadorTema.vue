<script setup>
import { computed } from 'vue'

import { useTema } from '@/composables/useTema'

const props = defineProps({
  // No topo escuro do site e do portal o botão precisa ser claro.
  claro: { type: Boolean, default: false },
})

const { tema, alternar } = useTema()

const escuro = computed(() => tema.value === 'escuro')
const rotulo = computed(() => (escuro.value ? 'Usar tema claro' : 'Usar tema escuro'))
</script>

<template>
  <button
    type="button"
    class="rounded-lg p-2 text-base transition"
    :class="
      props.claro
        ? 'text-white/80 ring-1 ring-white/25 hover:bg-white/10'
        : 'text-slate-600 hover:bg-slate-100'
    "
    :title="rotulo"
    :aria-label="rotulo"
    :aria-pressed="escuro"
    data-tour="alternar-tema"
    @click="alternar"
  >
    <span aria-hidden="true">{{ escuro ? '☀' : '☾' }}</span>
  </button>
</template>
