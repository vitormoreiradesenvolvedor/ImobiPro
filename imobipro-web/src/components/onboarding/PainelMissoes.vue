<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import { toursDisponiveis } from '@/onboarding/trilhas'
import { useAuthStore } from '@/stores/auth'
import { useOnboardingStore } from '@/stores/onboarding'

const onboarding = useOnboardingStore()
const auth = useAuthStore()
const router = useRouter()

const progresso = computed(() => onboarding.progresso)
const tours = computed(() => toursDisponiveis(auth.pode))

const porTrilha = computed(() => {
  const grupos = new Map()
  for (const missao of onboarding.missoes) {
    if (!grupos.has(missao.trilha)) {
      grupos.set(missao.trilha, {
        chave: missao.trilha,
        nome: missao.trilha_nome,
        icone: missao.trilha_icone,
        missoes: [],
      })
    }
    grupos.get(missao.trilha).missoes.push(missao)
  }
  return [...grupos.values()]
})

function irPara(missao) {
  onboarding.painelAberto = false
  router.push(missao.rota)
}

function comecarTour(id) {
  onboarding.iniciarTour(id, router)
}
</script>

<template>
  <div v-if="onboarding.painelAberto" class="fixed inset-0 z-[60]">
    <button
      type="button"
      class="absolute inset-0 cursor-default bg-slate-900/30"
      aria-label="Fechar guia"
      @click="onboarding.painelAberto = false"
    />

    <aside
      class="absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-white shadow-2xl sm:w-[26rem]"
      aria-label="Guia de uso"
    >
      <header class="border-b border-slate-200 p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-slate-900">Seu guia do ImobiPro</h2>
            <p class="text-sm text-slate-500">
              Missões conferidas no sistema de verdade não basta clicar aqui.
            </p>
          </div>
          <button
            type="button"
            class="rounded p-1 text-slate-400 hover:bg-slate-100"
            aria-label="Fechar"
            @click="onboarding.painelAberto = false"
          >
            ✕
          </button>
        </div>

        <div v-if="progresso" class="mt-4">
          <div class="flex items-baseline justify-between text-sm">
            <span class="font-semibold text-slate-800">{{ progresso.nivel }}</span>
            <span class="numerico text-slate-500">
              {{ progresso.pontos }} / {{ progresso.total_pontos }} pontos
            </span>
          </div>
          <div class="mt-2 h-2.5 rounded-full bg-slate-100">
            <div
              class="h-2.5 rounded-full bg-marca transition-all duration-700"
              :style="{ width: `${progresso.percentual}%` }"
            />
          </div>
          <p class="mt-1 text-xs text-slate-500">
            {{ progresso.concluidas }} de {{ progresso.total }} missões concluídas
          </p>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto p-5">
        <section
          v-if="progresso?.concluido"
          class="mb-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900 ring-1 ring-emerald-200"
        >
          <p class="font-semibold">Todas as missões cumpridas 🎉</p>
          <p class="mt-1">
            A imobiliária já rodou o ciclo inteiro: captação, funil, contrato, recebimento,
            repasse e vistoria.
          </p>
        </section>

        <section class="mb-6">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Tutoriais guiados
          </h3>
          <ul class="space-y-2">
            <li
              v-for="tour in tours"
              :key="tour.id"
              class="flex items-center justify-between gap-3 rounded-lg bg-slate-50 p-3"
            >
              <div class="min-w-0">
                <p class="text-sm font-medium text-slate-900">{{ tour.titulo }}</p>
                <p class="truncate text-xs text-slate-500">{{ tour.descricao }}</p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <span
                  v-if="progresso?.tours_concluidos?.includes(tour.id)"
                  class="text-xs text-emerald-600"
                  title="Tutorial concluído"
                >
                  ✓
                </span>
                <BaseButton variante="secundaria" @click="comecarTour(tour.id)">
                  {{ progresso?.tours_concluidos?.includes(tour.id) ? 'Rever' : 'Começar' }}
                </BaseButton>
              </div>
            </li>
          </ul>
        </section>

        <section v-for="trilha in porTrilha" :key="trilha.chave" class="mb-6">
          <h3
            class="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"
          >
            <span aria-hidden="true">{{ trilha.icone }}</span>
            {{ trilha.nome }}
          </h3>

          <ul class="space-y-2">
            <li
              v-for="missao in trilha.missoes"
              :key="missao.chave"
              class="rounded-lg p-3 ring-1 transition"
              :class="
                missao.concluida
                  ? 'bg-emerald-50/60 ring-emerald-200'
                  : missao.proxima
                    ? 'bg-white ring-marca'
                    : 'bg-white ring-slate-200'
              "
            >
              <div class="flex items-start gap-3">
                <span
                  class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full text-xs font-bold"
                  :class="
                    missao.concluida
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-200 text-slate-500'
                  "
                  aria-hidden="true"
                >
                  {{ missao.concluida ? '✓' : '' }}
                </span>

                <div class="min-w-0 flex-1">
                  <p
                    class="text-sm font-medium"
                    :class="
                      missao.concluida ? 'text-emerald-900 line-through' : 'text-slate-900'
                    "
                  >
                    {{ missao.titulo }}
                  </p>
                  <p class="mt-0.5 text-xs text-slate-600">{{ missao.descricao }}</p>

                  <p
                    v-if="missao.proxima"
                    class="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-600"
                  >
                    <strong class="text-slate-800">Como fazer:</strong> {{ missao.dica }}
                  </p>

                  <div class="mt-2 flex items-center gap-3">
                    <span class="numerico text-[11px] text-slate-400">
                      +{{ missao.pontos }} pontos
                    </span>
                    <button
                      v-if="!missao.concluida"
                      type="button"
                      class="text-xs font-medium text-marca hover:underline"
                      @click="irPara(missao)"
                    >
                      Ir para a tela →
                    </button>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </section>
      </div>

      <footer class="flex items-center justify-between gap-2 border-t border-slate-200 p-4">
        <button
          type="button"
          class="text-xs text-slate-500 hover:text-slate-700"
          @click="onboarding.reiniciar()"
        >
          Reiniciar tutoriais
        </button>
        <button
          type="button"
          class="text-xs text-slate-500 hover:text-slate-700"
          @click="onboarding.dispensar(!progresso?.dispensado)"
        >
          {{ progresso?.dispensado ? 'Reativar sugestões' : 'Não sugerir automaticamente' }}
        </button>
      </footer>
    </aside>
  </div>
</template>
