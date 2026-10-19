import { defineStore } from 'pinia'
import { computed, nextTick, ref } from 'vue'

import { onboardingService } from '@/services/api'
import { TOURS } from '@/onboarding/trilhas'

/** Espera o elemento aparecer na tela (a rota pode ter acabado de trocar). */
function aguardarElemento(seletor, tentativas = 20) {
  return new Promise((resolver) => {
    let restantes = tentativas
    const procurar = () => {
      const elemento = document.querySelector(seletor)
      if (elemento) return resolver(elemento)
      if (--restantes <= 0) return resolver(null)
      setTimeout(procurar, 100)
    }
    procurar()
  })
}

export const useOnboardingStore = defineStore('onboarding', () => {
  const progresso = ref(null)
  const carregando = ref(false)

  const tourAtivo = ref(null)
  const indicePasso = ref(0)
  const alvo = ref(null)
  const painelAberto = ref(false)
  const comemorando = ref(null)

  const missoes = computed(() => progresso.value?.missoes ?? [])
  const proximaMissao = computed(() => missoes.value.find((missao) => missao.proxima) ?? null)
  const passoAtual = computed(() => {
    if (!tourAtivo.value) return null
    return TOURS[tourAtivo.value]?.passos[indicePasso.value] ?? null
  })
  const totalPassos = computed(() =>
    tourAtivo.value ? TOURS[tourAtivo.value].passos.length : 0,
  )

  async function carregar() {
    carregando.value = true
    try {
      const { data } = await onboardingService.progresso()
      // Missão recém-cumprida vira comemoração na tela.
      const antes = new Set(
        (progresso.value?.missoes ?? []).filter((m) => m.concluida).map((m) => m.chave),
      )
      const nova = data.missoes.find((m) => m.concluida && !antes.has(m.chave))
      if (nova && progresso.value) comemorar(nova)

      progresso.value = data
    } finally {
      carregando.value = false
    }
  }

  function comemorar(missao) {
    comemorando.value = missao
    setTimeout(() => {
      if (comemorando.value?.chave === missao.chave) comemorando.value = null
    }, 6000)
  }

  async function iniciarTour(identificador, router) {
    if (!TOURS[identificador]) return

    tourAtivo.value = identificador
    indicePasso.value = 0
    painelAberto.value = false
    await posicionar(router)
  }

  async function posicionar(router) {
    const passo = passoAtual.value
    if (!passo) return

    if (passo.rota && router && router.currentRoute.value.path !== passo.rota) {
      await router.push(passo.rota)
    }

    await nextTick()
    alvo.value = passo.alvo ? await aguardarElemento(passo.alvo) : null
  }

  async function avancar(router) {
    if (indicePasso.value + 1 >= totalPassos.value) return encerrarTour(true)

    indicePasso.value += 1
    await posicionar(router)
    return undefined
  }

  async function voltar(router) {
    if (indicePasso.value === 0) return
    indicePasso.value -= 1
    await posicionar(router)
  }

  async function encerrarTour(concluido = false) {
    const identificador = tourAtivo.value
    tourAtivo.value = null
    alvo.value = null
    indicePasso.value = 0

    if (concluido && identificador) {
      const { data } = await onboardingService.concluirTour(identificador)
      progresso.value = data
    }
  }

  async function dispensar(dispensado = true) {
    const { data } = await onboardingService.dispensar(dispensado)
    progresso.value = data
  }

  async function reiniciar() {
    const { data } = await onboardingService.reiniciar()
    progresso.value = data
  }

  /** Abre o tour de boas-vindas na primeira vez que o usuário entra. */
  /**
   * Abre o tutorial de boas-vindas no primeiro acesso.
   *
   * Só quando o usuário ainda está no painel inicial: o guia leva para a rota
   * do primeiro passo, e quem já clicou em outra tela seria puxado de volta
   * sem ter pedido nada.
   */
  async function sugerirPrimeiroTour(router) {
    if (!progresso.value || progresso.value.dispensado) return
    if (progresso.value.tours_concluidos.includes('primeiros-passos')) return
    if (router?.currentRoute?.value?.path !== '/') return

    await iniciarTour('primeiros-passos', router)
  }

  // Uma escrita no sistema pode ter cumprido missão: reavalia sem esperar
  // troca de tela.
  // Recarrega sozinho depois de cada escrita; se a sessão já acabou, ignora.
  window.addEventListener('dados-alterados', () => {
    carregar().catch(() => undefined)
  })

  return {
    progresso,
    carregando,
    missoes,
    proximaMissao,
    tourAtivo,
    indicePasso,
    totalPassos,
    passoAtual,
    alvo,
    painelAberto,
    comemorando,
    carregar,
    iniciarTour,
    avancar,
    voltar,
    encerrarTour,
    dispensar,
    reiniciar,
    sugerirPrimeiroTour,
  }
})
