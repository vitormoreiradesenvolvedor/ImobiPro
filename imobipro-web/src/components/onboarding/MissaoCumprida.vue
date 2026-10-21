<script setup>
import { computed } from 'vue'

import { useOnboardingStore } from '@/stores/onboarding'

const onboarding = useOnboardingStore()

const missao = computed(() => onboarding.comemorando)
const progresso = computed(() => onboarding.progresso)
</script>

<template>
  <!-- Comemoração some sozinha; serve de reforço, não de bloqueio. -->
  <output
    v-if="missao"
    class="fixed bottom-6 left-1/2 z-[65] block w-[min(92vw,26rem)] -translate-x-1/2 rounded-xl bg-slate-900 p-4 text-white shadow-2xl"
  >
    <div class="flex items-start gap-3">
      <span class="text-2xl" aria-hidden="true">🎯</span>
      <div class="min-w-0 flex-1">
        <p class="text-sm font-bold">Missão cumprida!</p>
        <p class="text-sm text-slate-200">{{ missao.titulo }}</p>

        <div v-if="progresso" class="mt-3">
          <div class="flex items-baseline justify-between text-xs text-slate-300">
            <span>+{{ missao.pontos }} pontos · {{ progresso.nivel }}</span>
            <span class="numerico">{{ progresso.percentual }}%</span>
          </div>
          <div class="mt-1 h-1.5 rounded-full bg-white/20">
            <div
              class="h-1.5 rounded-full bg-emerald-400 transition-all duration-700"
              :style="{ width: `${progresso.percentual}%` }"
            />
          </div>
        </div>
      </div>

      <button
        type="button"
        class="text-slate-400 hover:text-white"
        aria-label="Fechar aviso"
        @click="onboarding.comemorando = null"
      >
        ✕
      </button>
    </div>
  </output>
</template>
