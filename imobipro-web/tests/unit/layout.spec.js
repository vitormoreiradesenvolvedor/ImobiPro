import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AppHeader from '@/components/layout/AppHeader.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificacoesStore } from '@/stores/notificacoes'
import { useOnboardingStore } from '@/stores/onboarding'

const push = vi.fn()

vi.mock('vue-router', async () => {
  const real = await vi.importActual('vue-router')
  return {
    ...real,
    useRoute: () => ({ params: {}, query: {}, path: '/' }),
    useRouter: () => ({ push, back: vi.fn(), afterEach: vi.fn() }),
    RouterView: { template: '<div />' },
  }
})

function montar(componente) {
  const tela = mount(componente, {
    attachTo: document.body,
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: { RouterLink: { template: '<a><slot /></a>' }, RouterView: true },
    },
  })

  const auth = useAuthStore()
  auth.usuario = {
    nome_completo: 'Ana Ribeiro',
    papel: 'ADMIN',
    papel_display: 'Administrador',
    email: 'ana@horizonteimoveis.com.br',
  }
  auth.tenant = {
    razao_social: 'Horizonte Imóveis',
    nome_fantasia: 'Horizonte',
    subdominio: 'horizonte',
  }
  auth.permissoes = { ver_financeiro: true, ver_crm: true, gerenciar_usuarios: true }
  return tela
}

describe('AppHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function preparar() {
    const tela = montar(AppHeader)
    const notificacoes = useNotificacoesStore()
    notificacoes.itens = [
      {
        id: 'n1',
        titulo: 'Lead novo',
        descricao: 'Atenda em 15 min',
        lida: false,
        criado_em: '2026-08-19T10:00:00Z',
      },
    ]
    notificacoes.naoLidas = 1
    return tela
  }

  const sino = (tela) =>
    tela.findAll('button').find((b) => b.attributes('aria-label') === 'Notificações')

  it('abre o sino e lista as notificações não lidas', async () => {
    const tela = preparar()
    await sino(tela).trigger('click')
    await flushPromises()

    expect(tela.text()).toContain('Lead novo')
    expect(sino(tela).attributes('aria-expanded')).toBe('true')
  })

  it('fecha o menu suspenso com Esc', async () => {
    const tela = preparar()
    await sino(tela).trigger('click')

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(sino(tela).attributes('aria-expanded')).toBe('false')
    tela.unmount()
  })

  it('fecha o menu suspenso ao clicar fora do cabeçalho', async () => {
    const tela = preparar()
    await sino(tela).trigger('click')

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()

    expect(sino(tela).attributes('aria-expanded')).toBe('false')
    tela.unmount()
  })

  it('mantém o menu aberto quando o clique é dentro do cabeçalho', async () => {
    const tela = preparar()
    await sino(tela).trigger('click')

    await tela.find('header').trigger('click')
    await flushPromises()

    expect(sino(tela).attributes('aria-expanded')).toBe('true')
    tela.unmount()
  })

  it('sai da conta pelo menu do usuário', async () => {
    const tela = preparar()
    const auth = useAuthStore()
    auth.logout = vi.fn().mockResolvedValue(undefined)

    await flushPromises()
    const avatar = tela.findAll('button').find((b) => b.text().includes('Ana Ribeiro'))
    await avatar.trigger('click')
    await flushPromises()
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Sair')
      .trigger('click')
    await flushPromises()

    expect(auth.logout).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'login' })
    tela.unmount()
  })
})

describe('AppLayout', () => {
  it('não quebra quando notificações e guia falham (sessão encerrada)', async () => {
    const erros = []
    const aoErrar = (evento) => erros.push(evento)
    window.addEventListener('unhandledrejection', aoErrar)

    const tela = montar(AppLayout)
    const notificacoes = useNotificacoesStore()
    const onboarding = useOnboardingStore()
    notificacoes.carregar = vi.fn().mockRejectedValue(new Error('401'))
    onboarding.carregar = vi.fn().mockRejectedValue(new Error('401'))

    await flushPromises()

    expect(tela.html()).toBeTruthy()
    expect(erros).toEqual([])

    window.removeEventListener('unhandledrejection', aoErrar)
    tela.unmount()
  })
})
