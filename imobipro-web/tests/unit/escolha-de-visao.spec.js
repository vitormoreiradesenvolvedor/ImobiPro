import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { siteService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import EscolhaDeVisaoView from '@/views/EscolhaDeVisaoView.vue'

vi.mock('@/services/api', async () => {
  const real = await vi.importActual('@/services/api')
  return { ...real, siteService: { identidade: vi.fn() } }
})

function montar() {
  return mount(EscolhaDeVisaoView, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: { RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] } },
    },
  })
}

describe('EscolhaDeVisaoView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    siteService.identidade.mockResolvedValue({
      data: { nome: 'Horizonte Imóveis', logo: null, cor_primaria: '#0F766E' },
    })
    import.meta.env.VITE_IMOBILIARIA = 'horizonte'
  })

  it('oferece as duas portas, com a marca da imobiliária', async () => {
    const tela = montar()
    await flushPromises()

    expect(tela.text()).toContain('Horizonte Imóveis')
    expect(tela.get('[data-teste="visao-cliente"]').attributes('href')).toBe('/site/horizonte')
    expect(tela.get('[data-teste="visao-equipe"]').attributes('href')).toBe('/login')
  })

  it('quem já está autenticado vai direto ao painel', async () => {
    const tela = montar()
    const auth = useAuthStore()
    auth.usuario = { nome_completo: 'Ana Ribeiro', papel: 'ADMIN' }
    await flushPromises()

    expect(tela.get('[data-teste="visao-equipe"]').attributes('href')).toBe('/')
    expect(tela.text()).toContain('Abrir o painel')
  })

  it('sem imobiliária no endereço, só a porta da equipe aparece', async () => {
    import.meta.env.VITE_IMOBILIARIA = ''

    const tela = montar()
    await flushPromises()

    expect(tela.find('[data-teste="visao-cliente"]').exists()).toBe(false)
    expect(tela.find('[data-teste="visao-equipe"]').exists()).toBe(true)
  })
})
