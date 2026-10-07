import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  candidaturasService,
  imoveisService,
  portalService,
  siteService,
  ticketsService,
  usuariosService,
} from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import AtendimentoView from '@/views/atendimento/AtendimentoView.vue'
import CandidaturasView from '@/views/candidaturas/CandidaturasView.vue'
import PortalView from '@/views/portal/PortalView.vue'
import CandidaturaView from '@/views/site/CandidaturaView.vue'
import ImovelPublicoView from '@/views/site/ImovelPublicoView.vue'
import VitrineView from '@/views/site/VitrineView.vue'

vi.mock('@/services/api', async () => {
  const real = await vi.importActual('@/services/api')
  return {
    ...real,
    siteService: {
      identidade: vi.fn(),
      catalogo: vi.fn(),
      destaques: vi.fn(),
      imoveis: vi.fn(),
      imovel: vi.fn(),
      abrirTicket: vi.fn(),
      acompanharTicket: vi.fn(),
      candidatura: vi.fn(),
      enviarDocumento: vi.fn(),
    },
    portalService: {
      resumo: vi.fn(),
      contratos: vi.fn(),
      cobrancas: vi.fn(),
      vistorias: vi.fn(),
      chamados: vi.fn(),
      abrirChamado: vi.fn(),
      assinarVistoria: vi.fn(),
      urlContratoPdf: (id) => `/api/v1/meu/contratos/${id}/pdf/`,
    },
    ticketsService: {
      listar: vi.fn(),
      obter: vi.fn(),
      painel: vi.fn(),
      responder: vi.fn(),
      mudarSituacao: vi.fn(),
      reatribuir: vi.fn(),
    },
    candidaturasService: {
      listar: vi.fn(),
      obter: vi.fn(),
      criar: vi.fn(),
      painel: vi.fn(),
      conferir: vi.fn(),
      decidir: vi.fn(),
      gerarContrato: vi.fn(),
    },
    imoveisService: { ...real.imoveisService, listar: vi.fn() },
    usuariosService: { ...real.usuariosService, listar: vi.fn() },
  }
})

// Leaflet precisa de DOM com layout; no unitário basta saber que o mapa entrou.
vi.mock('@/components/site/MapaDoImovel.vue', () => ({
  default: { name: 'MapaDoImovel', template: '<div class="mapa-stub" />' },
}))

const push = vi.fn()
const replace = vi.fn()

vi.mock('vue-router', async () => {
  const real = await vi.importActual('vue-router')
  return {
    ...real,
    useRoute: () => ({
      params: { subdominio: 'horizonte', codigo: 'REF-000001', token: 'tok-123' },
      query: {},
    }),
    useRouter: () => ({ push, replace, back: vi.fn() }),
  }
})

function montar(componente, { papel = 'ADMIN' } = {}) {
  const tela = mount(componente, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
      mocks: { $route: { params: {}, query: {} }, $router: { push, replace } },
    },
  })

  const auth = useAuthStore()
  auth.usuario = { nome_completo: 'Ana Ribeiro', papel, email: 'ana@horizonteimoveis.com.br' }
  auth.tenant = { nome_fantasia: 'Horizonte Imóveis', subdominio: 'horizonte' }
  auth.permissoes = { ver_financeiro: true, ver_crm: true, usar_portal: papel === 'INQUILINO' }
  return tela
}

const lista = (itens) => ({ data: { results: itens, count: itens.length } })

const IMOVEL_LISTA = {
  id: 'i1',
  codigo: 'REF-000001',
  titulo: 'Apartamento 302 com varanda',
  bairro: 'Centro',
  cidade: 'Lavras',
  tipo_display: 'Apartamento',
  valor_locacao: '2500.00',
  quartos: 2,
  banheiros: 2,
  area_util: '68.00',
  foto_capa: 'http://localhost/foto.jpg',
}

const CATALOGO = {
  total: 1,
  por_finalidade: [{ valor: 'LOCACAO', rotulo: 'Locação', total: 1 }],
  por_tipo: [{ valor: 'APARTAMENTO', rotulo: 'Apartamento', total: 1 }],
  por_bairro: [{ valor: 'Centro', rotulo: 'Centro', total: 1 }],
  por_cidade: [{ valor: 'Lavras', rotulo: 'Lavras', total: 1 }],
  por_faixa_de_aluguel: [{ valor: '1500_3000', rotulo: 'R$ 1.500 a R$ 3.000', total: 1 }],
  quartos_disponiveis: [2],
}

const IDENTIDADE = {
  nome: 'Imobiliária Central',
  subdominio: 'horizonte',
  logo: null,
  cor_primaria: '#123456',
  creci: 'MG-1234-J',
  telefone: '3599990000',
  email_contato: 'contato@central.test',
}

beforeEach(() => {
  vi.clearAllMocks()
  siteService.identidade.mockResolvedValue({ data: IDENTIDADE })
  document.documentElement.style.removeProperty('--cor-primaria')
})

// ------------------------------------------------------------------- vitrine

describe('VitrineView', () => {
  beforeEach(() => {
    siteService.imoveis.mockResolvedValue(lista([IMOVEL_LISTA]))
    siteService.catalogo.mockResolvedValue({ data: CATALOGO })
    siteService.destaques.mockResolvedValue({ data: [IMOVEL_LISTA] })
  })

  it('veste a página com a marca da imobiliária', async () => {
    const tela = montar(VitrineView)
    await flushPromises()

    expect(tela.text()).toContain('Imobiliária Central')
    expect(tela.text()).toContain('CRECI MG-1234-J')
    expect(document.documentElement.style.getPropertyValue('--cor-primaria')).toBe('#123456')
  })

  it('site sem identidade ainda mostra os imóveis', async () => {
    siteService.identidade.mockRejectedValue(new Error('404'))

    const tela = montar(VitrineView)
    await flushPromises()

    expect(tela.text()).toContain('Apartamento 302 com varanda')
  })

  it('mostra o catálogo com a contagem de cada categoria', async () => {
    const tela = montar(VitrineView)
    await flushPromises()

    expect(tela.text()).toContain('Apartamento 302 com varanda')
    expect(tela.text()).toContain('Centro')
    expect(tela.text()).toContain('R$ 1.500 a R$ 3.000')
  })

  it('preço de locação aparece por mês', async () => {
    const tela = montar(VitrineView)
    await flushPromises()

    expect(tela.text()).toContain('/mês')
  })

  it('escolher categoria filtra e guarda o filtro na URL', async () => {
    const tela = montar(VitrineView)
    await flushPromises()

    const botao = tela.findAll('button').find((b) => b.text().startsWith('Centro'))
    await botao.trigger('click')
    await flushPromises()

    expect(replace).toHaveBeenCalled()
    expect(siteService.imoveis).toHaveBeenCalledWith(
      'horizonte',
      expect.objectContaining({ bairro: 'Centro' }),
    )
  })

  it('sem resultado, explica o que fazer em vez de deixar a tela vazia', async () => {
    siteService.imoveis.mockResolvedValue(lista([]))
    const tela = montar(VitrineView)
    await flushPromises()

    expect(tela.text()).toContain('Nenhum imóvel com esses filtros')
  })
})

// ------------------------------------------------------------ ficha pública

const IMOVEL_DETALHE = {
  ...IMOVEL_LISTA,
  descricao: 'Dois quartos e varanda.',
  finalidade_display: 'Locação',
  valor_condominio: '480.00',
  valor_iptu_mensal: '120.00',
  endereco: {
    logradouro: 'Rua Central',
    numero: '302',
    bairro: 'Centro',
    cidade: 'Lavras',
    uf: 'MG',
    latitude: '-21.245',
    longitude: '-44.997',
  },
  fotos: [{ id: 'f1', arquivo: 'http://localhost/f1.jpg', legenda: 'Sala' }],
  midias: [
    { id: 'm1', tipo: 'BANNER', destaque: true, arquivo: 'http://localhost/banner.jpg' },
    { id: 'm2', tipo: 'VIDEO', arquivo: 'http://localhost/tour.mp4', titulo: 'Tour' },
  ],
  caracteristicas_detalhe: [{ id: 'c1', nome: 'Varanda' }],
}

describe('ImovelPublicoView', () => {
  beforeEach(() => {
    siteService.imovel.mockResolvedValue({ data: IMOVEL_DETALHE })
  })

  it('mostra galeria, vídeo e mapa do anúncio', async () => {
    const tela = montar(ImovelPublicoView)
    await flushPromises()

    expect(tela.find('video').exists()).toBe(true)
    expect(tela.find('.mapa-stub').exists()).toBe(true)
    expect(tela.text()).toContain('Onde fica')
  })

  it('pedido de visita devolve o protocolo para acompanhar', async () => {
    siteService.abrirTicket.mockResolvedValue({ data: { protocolo: 'ATD-2026-000001' } })
    const tela = montar(ImovelPublicoView)
    await flushPromises()

    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(siteService.abrirTicket).toHaveBeenCalled()
    expect(tela.text()).toContain('ATD-2026-000001')
  })

  it('erro da API vira mensagem na tela, não silêncio', async () => {
    siteService.abrirTicket.mockRejectedValue({
      response: { data: { campos: { solicitante_telefone: ['Informe um telefone.'] } } },
    })
    const tela = montar(ImovelPublicoView)
    await flushPromises()

    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(tela.text()).toContain('Informe um telefone.')
  })
})

// -------------------------------------------------------- portal do pretendente

const CANDIDATURA = {
  protocolo: 'CAD-2026-000001',
  status: 'RASCUNHO',
  status_display: 'Aguardando documentos',
  imovel_codigo: 'REF-000001',
  imovel_titulo: 'Apartamento 302',
  imovel_valor: '2500.00',
  documentos: [],
  documentos_pendentes: [
    { valor: 'IDENTIDADE', rotulo: 'Documento de identidade' },
    { valor: 'CPF', rotulo: 'CPF' },
  ],
  eventos: [{ id: 'e1', descricao: 'Candidatura aberta.', criado_em: '2026-08-19T10:00:00Z' }],
}

describe('CandidaturaView (link do pretendente)', () => {
  it('lista o que falta enviar', async () => {
    siteService.candidatura.mockResolvedValue({ data: CANDIDATURA })
    const tela = montar(CandidaturaView)
    await flushPromises()

    expect(tela.text()).toContain('Documento de identidade')
    expect(tela.text()).toContain('Estamos aguardando seus documentos.')
  })

  it('documento recusado aparece com o motivo do reenvio', async () => {
    siteService.candidatura.mockResolvedValue({
      data: {
        ...CANDIDATURA,
        status: 'PENDENTE',
        status_display: 'Pendência com o cliente',
        documentos: [
          {
            id: 'd1',
            tipo: 'IDENTIDADE',
            tipo_display: 'Documento de identidade',
            status: 'RECUSADO',
            status_display: 'Recusado',
            observacao: 'Foto ilegível.',
          },
        ],
      },
    })
    const tela = montar(CandidaturaView)
    await flushPromises()

    expect(tela.text()).toContain('Precisa reenviar')
    expect(tela.text()).toContain('Foto ilegível.')
  })

  it('link inválido avisa em vez de mostrar tela quebrada', async () => {
    siteService.candidatura.mockRejectedValue(new Error('404'))
    const tela = montar(CandidaturaView)
    await flushPromises()

    expect(tela.text()).toContain('Link inválido ou expirado')
  })
})

// --------------------------------------------------------- portal do inquilino

const RESUMO = {
  nome: 'Paulo Henrique Souza',
  contratos_ativos: 1,
  cobrancas_em_aberto: 1,
  chamados_abertos: 0,
  vistorias_a_assinar: 1,
  contrato_atual: {
    id: 'ct1',
    numero: 'LOC-2026-0001',
    status_display: 'Ativo',
    imovel_titulo: 'Apartamento 302',
    imovel_endereco: 'Rua Central, 302 · Centro · Lavras/MG',
    valor: '2500.00',
    dia_vencimento: 10,
    data_inicio: '2026-08-01',
    data_fim: '2027-08-01',
    proximo_reajuste_em: '2027-08-01',
  },
  proxima_cobranca: null,
}

const COBRANCA = {
  id: 'cb1',
  competencia: '2026-09-01',
  vencimento: '2026-09-10',
  valor_total: '3061.60',
  valor_multa: '0.00',
  valor_juros: '0.00',
  status: 'ABERTA',
  status_display: 'Aberta',
  dias_de_atraso: 0,
  pix_copia_cola: '00020126...',
  linha_digitavel: '34191.79001',
}

describe('PortalView (inquilino)', () => {
  beforeEach(() => {
    portalService.resumo.mockResolvedValue({ data: RESUMO })
    portalService.cobrancas.mockResolvedValue(lista([COBRANCA]))
    portalService.chamados.mockResolvedValue(lista([]))
    portalService.vistorias.mockResolvedValue(lista([]))
  })

  it('abre no contrato do cliente', async () => {
    const tela = montar(PortalView, { papel: 'INQUILINO' })
    await flushPromises()

    expect(tela.text()).toContain('LOC-2026-0001')
    expect(tela.text()).toContain('Rua Central, 302')
  })

  it('boletos mostram o que está a pagar com Pix e código de barras', async () => {
    const tela = montar(PortalView, { papel: 'INQUILINO' })
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Boletos')
      .trigger('click')
    await flushPromises()

    // Intl usa espaço não-quebrável entre "R$" e o número.
    const texto = tela.text().replace(/\u00a0/g, ' ')
    expect(texto).toContain('A pagar')
    expect(texto).toContain('R$ 3.061,60')
    expect(tela.findAll('button').some((b) => b.text() === 'Copiar Pix')).toBe(true)
  })

  it('abre chamado de manutenção pelo portal', async () => {
    portalService.abrirChamado.mockResolvedValue({ data: {} })
    const tela = montar(PortalView, { papel: 'INQUILINO' })
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Chamados')
      .trigger('click')
    await tela.find('textarea').setValue('Infiltração no banheiro.')
    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(portalService.abrirChamado).toHaveBeenCalledWith('Infiltração no banheiro.')
  })

  it('laudo finalizado pode ser assinado pelo cliente', async () => {
    portalService.vistorias.mockResolvedValue(
      lista([
        {
          id: 'v1',
          tipo_display: 'Vistoria de entrada',
          status: 'FINALIZADA',
          status_display: 'Finalizada',
          realizada_em: '2026-08-01',
          total_itens: 37,
          itens_com_problema: 0,
          assinatura_locatario: false,
        },
      ]),
    )
    portalService.assinarVistoria.mockResolvedValue({ data: {} })
    const tela = montar(PortalView, { papel: 'INQUILINO' })
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Vistorias')
      .trigger('click')
    await flushPromises()
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Assinar laudo')
      .trigger('click')
    await flushPromises()

    expect(portalService.assinarVistoria).toHaveBeenCalledWith('v1')
  })
})

// ------------------------------------------------------------- atendimento

const TICKET = {
  id: 't1',
  protocolo: 'ATD-2026-000001',
  tipo_display: 'Agendamento de visita',
  status: 'ABERTO',
  status_display: 'Aberto',
  solicitante_nome: 'Marina Interessada',
  solicitante_telefone: '35991234567',
  imovel_codigo: 'REF-000001',
  imovel_titulo: 'Apartamento 302',
  analista_nome: 'Carla Dias',
  sla_estourado: false,
  minutos_para_resposta: 12,
  mensagem: 'Posso visitar no sábado?',
  eventos: [],
}

describe('AtendimentoView', () => {
  beforeEach(() => {
    ticketsService.listar.mockResolvedValue(lista([TICKET]))
    ticketsService.painel.mockResolvedValue({
      data: { abertos: 1, sem_resposta: 1, sla_estourado: 0, agendados_hoje: 0, fila: [] },
    })
    ticketsService.obter.mockResolvedValue({ data: TICKET })
    usuariosService.listar.mockResolvedValue(lista([{ id: 'u1', nome_completo: 'Carla Dias' }]))
  })

  it('mostra a fila com o prazo de cada pedido', async () => {
    const tela = montar(AtendimentoView)
    await flushPromises()

    expect(tela.text()).toContain('ATD-2026-000001')
    expect(tela.text()).toContain('12 min')
  })

  it('prazo estourado aparece como atraso, não como número solto', async () => {
    ticketsService.listar.mockResolvedValue(
      lista([{ ...TICKET, sla_estourado: true, minutos_para_resposta: -20 }]),
    )
    const tela = montar(AtendimentoView)
    await flushPromises()

    expect(tela.text()).toContain('atrasado 20 min')
  })

  it('responder envia o retorno ao interessado', async () => {
    ticketsService.responder.mockResolvedValue({ data: { ...TICKET, eventos: [] } })
    const tela = montar(AtendimentoView)
    await flushPromises()

    await tela.find('table tbody tr').trigger('click')
    await flushPromises()
    await tela.find('textarea').setValue('Podemos sábado às 10h.')
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Registrar')
      .trigger('click')
    await flushPromises()

    expect(ticketsService.responder).toHaveBeenCalledWith('t1', 'Podemos sábado às 10h.', true)
  })
})

// ------------------------------------------------------------ candidaturas

const CANDIDATURA_INTERNA = {
  id: 'c1',
  protocolo: 'CAD-2026-000001',
  status: 'EM_ANALISE',
  status_display: 'Em análise',
  imovel_codigo: 'REF-000001',
  imovel_titulo: 'Apartamento 302',
  pretendente_nome: 'Marina Interessada',
  pretendente_telefone: '35991234567',
  renda_mensal: '9000.00',
  relacao_renda_aluguel: 3.6,
  documentacao_completa: true,
  link_do_cliente: 'http://localhost:8080/candidatura/horizonte/tok-123',
  documentos: [
    {
      id: 'd1',
      tipo_display: 'Documento de identidade',
      status: 'ENVIADO',
      status_display: 'Enviado, aguardando conferência',
      arquivo: 'http://localhost/doc.pdf',
      observacao: '',
    },
  ],
  documentos_pendentes: [],
  eventos: [],
}

describe('CandidaturasView', () => {
  beforeEach(() => {
    candidaturasService.listar.mockResolvedValue(lista([CANDIDATURA_INTERNA]))
    candidaturasService.painel.mockResolvedValue({
      data: {
        aguardando_documentos: 0,
        em_analise: 1,
        com_pendencia: 0,
        aprovadas_sem_contrato: 0,
      },
    })
    candidaturasService.obter.mockResolvedValue({ data: CANDIDATURA_INTERNA })
    imoveisService.listar.mockResolvedValue(lista([IMOVEL_LISTA]))
  })

  it('mostra a relação entre renda e aluguel na fila', async () => {
    const tela = montar(CandidaturasView)
    await flushPromises()

    expect(tela.text()).toContain('3.6x')
  })

  it('aprovar fica bloqueado enquanto houver documento sem conferência', async () => {
    const tela = montar(CandidaturasView)
    await flushPromises()

    await tela.find('table tbody tr').trigger('click')
    await flushPromises()

    const aprovar = tela.findAll('button').find((b) => b.text() === 'Aprovar')
    expect(aprovar.element.disabled).toBe(true)
  })

  it('conferir documento chama a API com aprovação', async () => {
    candidaturasService.conferir.mockResolvedValue({ data: CANDIDATURA_INTERNA })
    const tela = montar(CandidaturasView)
    await flushPromises()

    await tela.find('table tbody tr').trigger('click')
    await flushPromises()
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Conferir')
      .trigger('click')
    await flushPromises()

    expect(candidaturasService.conferir).toHaveBeenCalledWith('c1', 'd1', true)
  })

  it('recusa exige motivo antes de enviar', async () => {
    const tela = montar(CandidaturasView)
    await flushPromises()

    await tela.find('table tbody tr').trigger('click')
    await flushPromises()
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Recusar')
      .trigger('click')
    await flushPromises()

    const confirmar = tela.findAll('button').find((b) => b.text() === 'Recusar documento')
    expect(confirmar.element.disabled).toBe(true)
    expect(candidaturasService.conferir).not.toHaveBeenCalled()
  })
})
