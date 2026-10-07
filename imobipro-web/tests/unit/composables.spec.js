import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { useListagem } from '@/composables/useListagem'
import { useToast } from '@/composables/useToast'
import { notificacoesService } from '@/services/api'
import { useNotificacoesStore } from '@/stores/notificacoes'

vi.mock('@/services/api', () => ({
  notificacoesService: {
    listar: vi.fn(),
    naoLidas: vi.fn(),
    marcarLida: vi.fn(),
    marcarTodasLidas: vi.fn(),
  },
}))

describe('useListagem', () => {
  const paginado = (itens, total = itens.length) => ({
    data: { results: itens, count: total },
  })

  it('carrega a primeira página e conta o total', async () => {
    const carregador = vi.fn().mockResolvedValue(paginado([{ id: 1 }, { id: 2 }], 42))
    const lista = useListagem(carregador)

    await lista.carregar()

    expect(lista.itens.value).toHaveLength(2)
    expect(lista.total.value).toBe(42)
    expect(lista.totalPaginas.value).toBe(3)
    expect(carregador).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('descarta filtros vazios antes de chamar a API', async () => {
    const carregador = vi.fn().mockResolvedValue(paginado([]))
    const lista = useListagem(carregador, {
      filtrosIniciais: { search: '', tipo: 'CASA', situacao: null },
    })

    await lista.carregar()

    expect(carregador).toHaveBeenCalledWith({ page: 1, page_size: 20, tipo: 'CASA' })
  })

  it('aceita resposta sem paginação (endpoints agregados)', async () => {
    const carregador = vi.fn().mockResolvedValue({ data: [{ id: 1 }] })
    const lista = useListagem(carregador)

    await lista.carregar()

    expect(lista.total.value).toBe(1)
  })

  it('marca vazio e guarda o erro quando a API falha', async () => {
    const carregador = vi.fn().mockRejectedValue(new Error('500'))
    const lista = useListagem(carregador)

    await lista.carregar()

    expect(lista.vazio.value).toBe(true)
    expect(lista.erro.value).toBeInstanceOf(Error)
  })

  it('espera o usuário parar de digitar antes de refazer a busca', async () => {
    vi.useFakeTimers()
    const carregador = vi.fn().mockResolvedValue(paginado([]))
    const lista = useListagem(carregador, { filtrosIniciais: { search: '' } })

    lista.filtros.value.search = 'c'
    await nextTick()
    lista.filtros.value.search = 'cob'
    await nextTick()
    expect(carregador).not.toHaveBeenCalled()

    vi.advanceTimersByTime(400)
    expect(carregador).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('volta para a página 1 quando o filtro muda', async () => {
    vi.useFakeTimers()
    const carregador = vi.fn().mockResolvedValue(paginado([], 100))
    const lista = useListagem(carregador, { filtrosIniciais: { search: '' } })
    lista.pagina.value = 3

    lista.filtros.value.search = 'x'
    await nextTick()
    vi.advanceTimersByTime(400)

    expect(lista.pagina.value).toBe(1)
    vi.useRealTimers()
  })
})

describe('useToast', () => {
  it('extrai a mensagem de campo do erro de validação do DRF', () => {
    const { mensagemDoErro } = useToast()

    const mensagem = mensagemDoErro({
      response: {
        data: {
          detail: 'Dados inválidos.',
          code: 'validacao',
          campos: { cpf_cnpj: ['CPF inválido.'] },
        },
      },
    })

    // Agora a mensagem diz de qual campo veio o erro.
    expect(mensagem).toBe('cpf_cnpj: CPF inválido.')
  })

  it('encontra a mensagem em erro aninhado (endereço dentro de pessoa)', () => {
    const { mensagemDoErro } = useToast()

    const mensagem = mensagemDoErro({
      response: {
        data: {
          detail: 'Dados inválidos.',
          code: 'validacao',
          campos: { endereco: { cidade: ['Este campo não pode ser em branco.'] } },
        },
      },
    })

    expect(mensagem).toBe('endereco › cidade: Este campo não pode ser em branco.')
  })

  it('usa o detail quando o erro não é de validação', () => {
    const { mensagemDoErro } = useToast()

    expect(
      mensagemDoErro({ response: { data: { detail: 'Sessão expirada.', code: 'jwt' } } }),
    ).toBe('Sessão expirada.')
  })

  it('cai na mensagem alternativa quando não há resposta', () => {
    const { mensagemDoErro } = useToast()

    expect(mensagemDoErro(new Error('rede'), 'Sem conexão.')).toBe('Sem conexão.')
  })

  it('remove o aviso sozinho depois do tempo', () => {
    vi.useFakeTimers()
    const { sucesso, avisos } = useToast()

    const id = sucesso('ok')
    expect(avisos.value.some((a) => a.id === id)).toBe(true)

    vi.advanceTimersByTime(5000)
    expect(avisos.value.some((a) => a.id === id)).toBe(false)
    vi.useRealTimers()
  })
})

describe('store de notificações', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('carrega lista e contador', async () => {
    notificacoesService.listar.mockResolvedValue({
      data: { results: [{ id: 'n1', titulo: 'Novo lead', lida: false }] },
    })
    notificacoesService.naoLidas.mockResolvedValue({ data: { nao_lidas: 1 } })
    const store = useNotificacoesStore()

    await store.carregar()

    expect(store.recentes).toHaveLength(1)
    expect(store.naoLidas).toBe(1)
  })

  it('marcar como lida abate o contador', async () => {
    notificacoesService.listar.mockResolvedValue({
      data: { results: [{ id: 'n1', titulo: 'Novo lead', lida: false }] },
    })
    notificacoesService.naoLidas.mockResolvedValue({ data: { nao_lidas: 1 } })
    notificacoesService.marcarLida.mockResolvedValue({})
    const store = useNotificacoesStore()
    await store.carregar()

    await store.marcarLida('n1')

    expect(store.naoLidas).toBe(0)
    expect(store.itens[0].lida).toBe(true)
  })

  it('marcar todas zera o contador', async () => {
    notificacoesService.listar.mockResolvedValue({
      data: {
        results: [
          { id: 'n1', lida: false },
          { id: 'n2', lida: false },
        ],
      },
    })
    notificacoesService.naoLidas.mockResolvedValue({ data: { nao_lidas: 2 } })
    notificacoesService.marcarTodasLidas.mockResolvedValue({})
    const store = useNotificacoesStore()
    await store.carregar()

    await store.marcarTodasLidas()

    expect(store.naoLidas).toBe(0)
  })

  it('desconectar limpa a lista', async () => {
    notificacoesService.listar.mockResolvedValue({ data: { results: [{ id: 'n1' }] } })
    notificacoesService.naoLidas.mockResolvedValue({ data: { nao_lidas: 1 } })
    const store = useNotificacoesStore()
    await store.carregar()

    store.desconectar()

    expect(store.itens).toHaveLength(0)
    expect(store.naoLidas).toBe(0)
  })

  it('não abre WebSocket sem token', () => {
    const store = useNotificacoesStore()

    store.conectar(null)

    expect(store.conectado).toBe(false)
  })
})
