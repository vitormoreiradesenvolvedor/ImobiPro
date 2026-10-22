import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BotaoTutorial from '@/components/onboarding/BotaoTutorial.vue'
import MissaoCumprida from '@/components/onboarding/MissaoCumprida.vue'
import PainelMissoes from '@/components/onboarding/PainelMissoes.vue'
import TourOverlay from '@/components/onboarding/TourOverlay.vue'
import { TOURS, toursDisponiveis } from '@/onboarding/trilhas'
import { onboardingService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useOnboardingStore } from '@/stores/onboarding'

vi.mock('@/services/api', () => ({
  onboardingService: {
    progresso: vi.fn(),
    concluirTour: vi.fn(),
    dispensar: vi.fn(),
    reiniciar: vi.fn(),
  },
}))

const push = vi.fn()
vi.mock('vue-router', async () => {
  const real = await vi.importActual('vue-router')
  return {
    ...real,
    useRouter: () => ({ push, currentRoute: { value: { path: '/' } } }),
  }
})

/** Cria no DOM os elementos que o tour procura. */
function montarAlvos(tourId) {
  for (const passo of TOURS[tourId].passos) {
    const nome = passo.alvo.replace('[data-tour="', '').replace('"]', '')
    if (document.querySelector(passo.alvo)) continue
    const elemento = document.createElement('div')
    elemento.setAttribute('data-tour', nome)
    document.body.appendChild(elemento)
  }
}

const missao = (chave, extras = {}) => ({
  chave,
  titulo: `Missão ${chave}`,
  descricao: 'descrição',
  dica: 'dica prática',
  trilha: 'carteira',
  trilha_nome: 'Montar a carteira',
  trilha_icone: '⌂',
  rota: '/pessoas',
  pontos: 10,
  concluida: false,
  proxima: false,
  ...extras,
})

const progressoFalso = (extras = {}) => ({
  missoes: [missao('cadastrar_pessoa', { proxima: true }), missao('captar_imovel')],
  trilhas: [
    { chave: 'carteira', nome: 'Montar a carteira', icone: '⌂', total: 2, concluidas: 0 },
  ],
  concluidas: 0,
  total: 2,
  pontos: 0,
  total_pontos: 20,
  percentual: 0,
  nivel: 'Começando',
  proxima_missao: 'cadastrar_pessoa',
  tours_concluidos: [],
  dispensado: false,
  concluido: false,
  ...extras,
})

// O TourOverlay mantém um intervalo de remedição enquanto está montado; sem
// desmontar, ele continuaria disparando depois do fim do teste.
const montados = []

function montar(componente) {
  const wrapper = mount(componente, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
    attachTo: document.body,
  })
  montados.push(wrapper)
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

afterEach(() => {
  while (montados.length) montados.pop().unmount()
})

describe('roteiros', () => {
  it('todo passo aponta para um alvo e traz texto explicativo', () => {
    for (const [id, tour] of Object.entries(TOURS)) {
      expect(tour.passos.length, `${id} sem passos`).toBeGreaterThan(0)
      for (const passo of tour.passos) {
        expect(passo.titulo, `${id}: passo sem título`).toBeTruthy()
        expect(passo.texto.length, `${id}: texto curto demais`).toBeGreaterThan(30)
        expect(passo.alvo, `${id}: passo sem alvo`).toMatch(/^\[data-tour=/)
      }
    }
  })

  it('esconde o tour financeiro de quem não tem a permissão', () => {
    const doCorretor = toursDisponiveis(() => false).map((t) => t.id)
    const doAdmin = toursDisponiveis(() => true).map((t) => t.id)

    expect(doCorretor).not.toContain('rodar-financeiro')
    expect(doAdmin).toContain('rodar-financeiro')
  })
})

describe('store de onboarding', () => {
  it('carrega o progresso da API', async () => {
    onboardingService.progresso.mockResolvedValue({ data: progressoFalso() })
    const store = useOnboardingStore()

    await store.carregar()

    expect(store.missoes).toHaveLength(2)
    expect(store.proximaMissao.chave).toBe('cadastrar_pessoa')
  })

  it('comemora quando uma missão passa a concluída', async () => {
    onboardingService.progresso.mockResolvedValueOnce({ data: progressoFalso() })
    const store = useOnboardingStore()
    await store.carregar()

    onboardingService.progresso.mockResolvedValueOnce({
      data: progressoFalso({
        missoes: [missao('cadastrar_pessoa', { concluida: true }), missao('captar_imovel')],
        concluidas: 1,
        pontos: 10,
        percentual: 50,
      }),
    })
    await store.carregar()

    expect(store.comemorando.chave).toBe('cadastrar_pessoa')
  })

  it('não comemora na primeira carga', async () => {
    onboardingService.progresso.mockResolvedValue({
      data: progressoFalso({
        missoes: [missao('cadastrar_pessoa', { concluida: true })],
        concluidas: 1,
      }),
    })
    const store = useOnboardingStore()

    await store.carregar()

    expect(store.comemorando).toBeNull()
  })

  it('anda para frente e para trás no tour', async () => {
    montarAlvos('primeiros-passos')
    const store = useOnboardingStore()
    await store.iniciarTour('primeiros-passos', null)
    expect(store.indicePasso).toBe(0)

    await store.avancar(null)
    expect(store.indicePasso).toBe(1)

    await store.voltar(null)
    expect(store.indicePasso).toBe(0)
  })

  it('não retrocede antes do primeiro passo', async () => {
    const store = useOnboardingStore()
    await store.iniciarTour('primeiros-passos', null)

    await store.voltar(null)

    expect(store.indicePasso).toBe(0)
  })

  it('conclui o tour ao passar do último passo', async () => {
    onboardingService.concluirTour.mockResolvedValue({
      data: progressoFalso({ tours_concluidos: ['funil-de-vendas'] }),
    })
    montarAlvos('funil-de-vendas')
    const store = useOnboardingStore()
    await store.iniciarTour('funil-de-vendas', null)

    const total = store.totalPassos
    for (let i = 0; i < total; i += 1) await store.avancar(null)

    expect(onboardingService.concluirTour).toHaveBeenCalledWith('funil-de-vendas')
    expect(store.tourAtivo).toBeNull()
  })

  it('sair pelo X não marca o tour como concluído', async () => {
    const store = useOnboardingStore()
    await store.iniciarTour('primeiros-passos', null)

    await store.encerrarTour(false)

    expect(onboardingService.concluirTour).not.toHaveBeenCalled()
    expect(store.tourAtivo).toBeNull()
  })

  /** Roteador falso: o que importa é em qual tela o usuário está agora. */
  const roteador = (caminho = '/') => ({
    push: vi.fn(),
    currentRoute: { value: { path: caminho } },
  })

  it('sugere o tour de boas-vindas só na primeira vez', async () => {
    onboardingService.progresso.mockResolvedValue({ data: progressoFalso() })
    const store = useOnboardingStore()
    await store.carregar()

    await store.sugerirPrimeiroTour(roteador())
    expect(store.tourAtivo).toBe('primeiros-passos')

    await store.encerrarTour(false)
    store.progresso.tours_concluidos = ['primeiros-passos']
    await store.sugerirPrimeiroTour(roteador())

    expect(store.tourAtivo).toBeNull()
  })

  it('não puxa de volta quem já saiu do painel inicial', async () => {
    // O tour navega para a rota do primeiro passo; abrir sozinho enquanto o
    // usuário está em outra tela desfaz o clique que ele acabou de dar.
    onboardingService.progresso.mockResolvedValue({ data: progressoFalso() })
    const store = useOnboardingStore()
    await store.carregar()

    await store.sugerirPrimeiroTour(roteador('/atendimento'))

    expect(store.tourAtivo).toBeNull()
  })

  it('respeita quem dispensou o guia', async () => {
    onboardingService.progresso.mockResolvedValue({
      data: progressoFalso({ dispensado: true }),
    })
    const store = useOnboardingStore()
    await store.carregar()

    await store.sugerirPrimeiroTour(null)

    expect(store.tourAtivo).toBeNull()
  })
})

describe('BotaoTutorial', () => {
  it('mostra quantas missões faltam', async () => {
    const tela = montar(BotaoTutorial)
    const store = useOnboardingStore()
    store.progresso = progressoFalso({ concluidas: 1, total: 4 })
    await tela.vm.$nextTick()

    expect(tela.text()).toContain('3')
  })

  it('abre e fecha o painel', async () => {
    const tela = montar(BotaoTutorial)
    const store = useOnboardingStore()

    await tela.find('button').trigger('click')
    expect(store.painelAberto).toBe(true)

    await tela.find('button').trigger('click')
    expect(store.painelAberto).toBe(false)
  })
})

describe('PainelMissoes', () => {
  it('lista missões por trilha, com dica na próxima', async () => {
    const tela = montar(PainelMissoes)
    const store = useOnboardingStore()
    const auth = useAuthStore()
    auth.permissoes = { ver_financeiro: true }
    store.progresso = progressoFalso()
    store.painelAberto = true
    await flushPromises()

    expect(tela.text()).toContain('Montar a carteira')
    expect(tela.text()).toContain('dica prática')
    expect(tela.text()).toContain('0 de 2 missões concluídas')
  })

  it('marca a missão concluída e some com a dica', async () => {
    const tela = montar(PainelMissoes)
    const store = useOnboardingStore()
    store.progresso = progressoFalso({
      missoes: [missao('cadastrar_pessoa', { concluida: true })],
      concluidas: 1,
      pontos: 10,
      percentual: 50,
    })
    store.painelAberto = true
    await flushPromises()

    expect(tela.find('.line-through').exists()).toBe(true)
    expect(tela.text()).not.toContain('Como fazer')
  })

  it('celebra quando tudo termina', async () => {
    const tela = montar(PainelMissoes)
    const store = useOnboardingStore()
    store.progresso = progressoFalso({ concluido: true, percentual: 100 })
    store.painelAberto = true
    await flushPromises()

    expect(tela.text()).toContain('Todas as missões cumpridas')
  })

  it('navega para a tela da missão', async () => {
    const tela = montar(PainelMissoes)
    const store = useOnboardingStore()
    store.progresso = progressoFalso()
    store.painelAberto = true
    await flushPromises()

    const ir = tela.findAll('button').find((b) => b.text().includes('Ir para a tela'))
    await ir.trigger('click')

    expect(push).toHaveBeenCalledWith('/pessoas')
    expect(store.painelAberto).toBe(false)
  })
})

describe('TourOverlay', () => {
  it('mostra passo, progresso e texto do roteiro', async () => {
    const tela = montar(TourOverlay)
    const store = useOnboardingStore()
    await store.iniciarTour('primeiros-passos', null)
    await flushPromises()

    expect(tela.text()).toContain('Passo 1 de 5')
    expect(tela.text()).toContain('O menu segue o fluxo do negócio')
  })

  it('no último passo o botão vira "Concluir"', async () => {
    const tela = montar(TourOverlay)
    const store = useOnboardingStore()
    await store.iniciarTour('primeiros-passos', null)
    store.indicePasso = store.totalPassos - 1
    await flushPromises()

    expect(tela.text()).toContain('Concluir')
  })

  it('passo com exigeClique pede a ação em vez de oferecer "Próximo"', async () => {
    const tela = montar(TourOverlay)
    const store = useOnboardingStore()
    await store.iniciarTour('captar-imovel', null)
    await flushPromises()

    expect(tela.text()).toContain('Clique no botão destacado')
    expect(tela.text()).not.toContain('Próximo')
  })
})

describe('MissaoCumprida', () => {
  it('aparece com a missão e o percentual', async () => {
    const tela = montar(MissaoCumprida)
    const store = useOnboardingStore()
    store.progresso = progressoFalso({ percentual: 50, nivel: 'Aprendiz' })
    store.comemorando = missao('cadastrar_pessoa', { concluida: true })
    await tela.vm.$nextTick()

    expect(tela.text()).toContain('Missão cumprida!')
    expect(tela.text()).toContain('Aprendiz')
    expect(tela.text()).toContain('50%')
  })

  it('não aparece sem missão recém-concluída', () => {
    const tela = montar(MissaoCumprida)

    expect(tela.text()).toBe('')
  })
})
