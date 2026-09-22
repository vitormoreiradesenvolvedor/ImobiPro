<script setup>
import { computed } from 'vue'

import { useOnboardingStore } from '@/stores/onboarding'

const onboarding = useOnboardingStore()

const progresso = computed(() => onboarding.progresso)
const pendentes = computed(() =>
  progresso.value ? progresso.value.total - progresso.value.concluidas : 0,
)
</script>

<template>
  <button
    type="button"
    data-tour="botao-tutorial"
    class="relative flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
    :aria-expanded="onboarding.painelAberto"
    title="Guia de uso e missões"
    @click="onboarding.painelAberto = !onboarding.painelAberto"
  >
    <span aria-hidden="true">🎓</span>
    <span class="hidden sm:inline">Tutorial</span>

    <span
      v-if="pendentes"
      class="grid size-5 place-items-center rounded-full bg-marca text-[10px] font-bold text-white"
      :title="`${pendentes} missões pendentes`"
    >
      {{ pendentes }}
    </span>
  </button>
</template>
