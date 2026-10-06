<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useOnboardingStore } from '@/stores/onboarding'

const onboarding = useOnboardingStore()
const router = useRouter()

const MARGEM = 8
const LARGURA_BALAO = 340

const recorte = ref(null)
const balao = ref({ top: 0, left: 0 })

const passo = computed(() => onboarding.passoAtual)
const numero = computed(() => onboarding.indicePasso + 1)
const total = computed(() => onboarding.totalPassos)
const percentual = computed(() => Math.round((numero.value / total.value) * 100))

/** Recalcula o buraco do spotlight e onde o balão cabe na tela. */
function medir() {
  const elemento = onboarding.alvo
  if (!elemento) {
    recorte.value = null
    balao.value = {
      top: window.innerHeight / 2 - 120,
      left: window.innerWidth / 2 - LARGURA_BALAO / 2,
    }
    return
  }

  const caixa = elemento.getBoundingClientRect()
  recorte.value = {
    top: caixa.top - MARGEM,
    left: caixa.left - MARGEM,
    width: caixa.width + MARGEM * 2,
    height: caixa.height + MARGEM * 2,
  }

  const posicao = passo.value?.posicao ?? 'baixo'
  const posicoes = {
    baixo: { top: caixa.bottom + 16, left: caixa.left },
    cima: { top: caixa.top - 16 - 210, left: caixa.left },
    direita: { top: caixa.top, left: caixa.right + 16 },
    esquerda: { top: caixa.top, left: caixa.left - LARGURA_BALAO - 16 },
  }
  const escolhida = posicoes[posicao] ?? posicoes.baixo

  // Mantém o balão dentro da janela, sem depender da posição pedida.
  balao.value = {
    top: Math.min(Math.max(16, escolhida.top), window.innerHeight - 240),
    left: Math.min(Math.max(16, escolhida.left), window.innerWidth - LARGURA_BALAO - 16),
  }
}

let observador

// Assim que o alvo é encontrado (ou muda de passo), reposiciona na hora sem
// isto o balão nascia no centro e só ia para o lugar no tick seguinte.
watch(
  () => onboarding.alvo,
  (elemento) => {
    medir()
    // scrollIntoView não existe em qualquer ambiente (jsdom, alvo fora do DOM):
    // rolar é conforto, não pode derrubar o tour.
    if (typeof elemento?.scrollIntoView === 'function') {
      elemento.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  },
  { immediate: true },
)

onMounted(() => {
  medir()
  window.addEventListener('resize', medir)
  window.addEventListener('scroll', medir, true)
  // Rede de segurança: o alvo pode mudar de tamanho (tabela carregando, modal).
  observador = setInterval(medir, 400)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', medir)
  window.removeEventListener('scroll', medir, true)
  clearInterval(observador)
})

/**
 * Passo "faça você mesmo": quem avança o roteiro é o clique no elemento real.
 *
 * O ouvinte precisa morar no próprio alvo a moldura desenhada por cima é
 * `pointer-events-none` de propósito, para o clique chegar ao botão de verdade,
 * e por isso nunca receberia o evento.
 */
let removerEscuta = null

function escutarCliqueNoAlvo() {
  removerEscuta?.()
  removerEscuta = null

  const elemento = onboarding.alvo
  if (!elemento || !passo.value?.exigeClique) return

  const aoClicar = () => onboarding.avancar(router)
  elemento.addEventListener('click', aoClicar, { once: true })
  removerEscuta = () => elemento.removeEventListener('click', aoClicar)
}

watch([() => onboarding.alvo, () => onboarding.indicePasso], escutarCliqueNoAlvo, {
  immediate: true,
})

onBeforeUnmount(() => removerEscuta?.())
</script>

<template>
  <dialog
    v-if="passo"
    open
    aria-modal="true"
    aria-label="Tutorial guiado"
    class="pointer-events-none fixed inset-0 z-[70] m-0 h-full max-h-none w-full max-w-none bg-transparent p-0"
  >
    <!-- Escurece tudo, menos o recorte do alvo -->
    <div
      class="paleta-fixa pointer-events-auto absolute inset-0 bg-slate-900/70 transition-opacity"
      :style="
        recorte
          ? {
              clipPath: `polygon(
                0% 0%, 0% 100%, ${recorte.left}px 100%,
                ${recorte.left}px ${recorte.top}px,
                ${recorte.left + recorte.width}px ${recorte.top}px,
                ${recorte.left + recorte.width}px ${recorte.top + recorte.height}px,
                ${recorte.left}px ${recorte.top + recorte.height}px,
                ${recorte.left}px 100%, 100% 100%, 100% 0%)`,
            }
          : {}
      "
    />

    <!-- Moldura do alvo: deixa o clique passar para o elemento real -->
    <div
      v-if="recorte"
      class="pointer-events-none absolute rounded-lg ring-4 ring-marca ring-offset-2 transition-all"
      :class="passo.exigeClique ? 'animate-pulse' : ''"
      :style="{
        top: `${recorte.top}px`,
        left: `${recorte.left}px`,
        width: `${recorte.width}px`,
        height: `${recorte.height}px`,
      }"
    />

    <!-- Balão -->
    <article
      class="pointer-events-auto absolute w-[340px] rounded-xl bg-white p-5 shadow-2xl"
      :style="{ top: `${balao.top}px`, left: `${balao.left}px` }"
    >
      <header class="mb-2 flex items-center justify-between gap-3">
        <span class="text-xs font-semibold uppercase tracking-wide text-marca">
          Passo {{ numero }} de {{ total }}
        </span>
        <button
          type="button"
          class="rounded p-1 text-slate-400 hover:bg-slate-100"
          aria-label="Fechar tutorial"
          @click="onboarding.encerrarTour(false)"
        >
          ✕
        </button>
      </header>

      <div class="mb-3 h-1.5 rounded-full bg-slate-100">
        <div
          class="h-1.5 rounded-full bg-marca transition-all"
          :style="{ width: `${percentual}%` }"
        />
      </div>

      <h2 class="text-base font-semibold text-slate-900">{{ passo.titulo }}</h2>
      <p class="mt-1 text-sm leading-relaxed text-slate-600">{{ passo.texto }}</p>

      <p
        v-if="passo.exigeClique"
        class="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800"
      >
        Clique no botão destacado para continuar.
      </p>

      <footer class="mt-4 flex items-center justify-between gap-2">
        <button
          type="button"
          class="text-sm text-slate-500 hover:text-slate-700"
          @click="onboarding.encerrarTour(false)"
        >
          Sair do tutorial
        </button>

        <div class="flex gap-2">
          <button
            v-if="numero > 1"
            type="button"
            class="rounded-lg px-3 py-1.5 text-sm ring-1 ring-slate-300 hover:bg-slate-50"
            @click="onboarding.voltar(router)"
          >
            Voltar
          </button>
          <button
            v-if="!passo.exigeClique"
            type="button"
            class="rounded-lg bg-marca px-4 py-1.5 text-sm font-semibold text-white hover:brightness-110"
            @click="onboarding.avancar(router)"
          >
            {{ numero === total ? 'Concluir' : 'Próximo' }}
          </button>
        </div>
      </footer>
    </article>
  </dialog>
</template>
