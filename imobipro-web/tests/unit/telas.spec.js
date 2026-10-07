import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  cobrancasService,
  comissoesService,
  contratosService,
  financeiroService,
  imoveisService,
  leadsService,
  pessoasService,
  repassesService,
  visitasService,
  vistoriasService,
} from '@/services/api'
import ContratosListView from '@/views/contratos/ContratosListView.vue'
import KanbanView from '@/views/crm/KanbanView.vue'
import CobrancasView from '@/views/financeiro/CobrancasView.vue'
import ComissoesView from '@/views/financeiro/ComissoesView.vue'
import RepassesView from '@/views/financeiro/RepassesView.vue'
import ImoveisListView from '@/views/imoveis/ImoveisListView.vue'
import PessoasView from '@/views/pessoas/PessoasView.vue'
import AgendaView from '@/views/agenda/AgendaView.vue'
import RelatoriosView from '@/views/relatorios/RelatoriosView.vue'
import VistoriasListView from '@/views/vistorias/VistoriasListView.vue'

vi.mock('@/services/api')
vi.mock('@/components/imoveis/MapaImoveis.vue', () => ({
  // Leaflet precisa de DOM real com layout; no unitário basta a presença.
  default: { name: 'MapaImoveis', template: '<div class="mapa-stub" />' },
}))

const rotas = {
  RouterLink: { template: '<a><slot /></a>' },
}

function montar(componente, extras = {}) {
  return mount(componente, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: rotas,
      mocks: {
        $route: { params: {}, query: {} },
        $router: { push: vi.fn(), back: vi.fn() },
      },
    },
    ...extras,
  })
}

const pagina = (itens, extras = {}) => ({
  data: { results: itens, count: itens.length, ...extras },
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ImoveisListView', () => {
  const imovel = {
    id: 'i1',
    codigo: 'REF-000001',
    titulo: 'Apartamento no Centro',
    finalidade: 'LOCACAO',
    situacao: 'DISPONIVEL',
    situacao_display: 'Disponível',
    valor_locacao: '2500.00',
    quartos: 2,
    bairro: 'Centro',
    cidade: 'Lavras',
  }

  it('mostra os cards da carteira', async () => {
    imoveisService.listar.mockResolvedValue(pagina([imovel]))
    const tela = montar(ImoveisListView)
    await flushPromises()

    expect(tela.text()).toContain('REF-000001')
    expect(tela.text()).toContain('1 imóveis na carteira')
  })

  it('convida a cadastrar quando a carteira está vazia', async () => {
    imoveisService.listar.mockResolvedValue(pagina([]))
    const tela = montar(ImoveisListView)
    await flushPromises()

    expect(tela.text()).toContain('Nenhum imóvel encontrado')
  })

  it('troca para tabela e depois para o mapa', async () => {
    imoveisService.listar.mockResolvedValue(pagina([imovel]))
    imoveisService.mapa.mockResolvedValue({ data: [imovel] })
    const tela = montar(ImoveisListView)
    await flushPromises()

    await tela.find('button[aria-pressed="false"]').trigger('click')
    expect(tela.find('table').exists()).toBe(true)

    const botoes = tela.findAll('button')
    await botoes.find((b) => b.text() === 'Mapa').trigger('click')
    await flushPromises()

    expect(tela.find('.mapa-stub').exists()).toBe(true)
    expect(imoveisService.mapa).toHaveBeenCalled()
  })
})

describe('KanbanView', () => {
  const coluna = (estagio, leads = []) => ({
    estagio,
    rotulo: estagio,
    total: leads.length,
    valor_total: '0',
    leads,
  })

  it('mostra o funil com as métricas do topo', async () => {
    leadsService.funil.mockResolvedValue({ data: [coluna('NOVO'), coluna('PROPOSTA')] })
    leadsService.estatisticas.mockResolvedValue({
      data: { abertos: 7, taxa_conversao: 50, sla_cumprido_percentual: 80 },
    })
    const tela = montar(KanbanView)
    await flushPromises()

    expect(tela.text()).toContain('7 leads abertos')
    expect(tela.text()).toContain('conversão 50%')
  })

  it('abre o diálogo de motivo ao perder um lead', async () => {
    const lead = { id: 'l1', nome: 'Fernanda', estagio: 'NOVO', temperatura: 'MORNO' }
    leadsService.funil.mockResolvedValue({ data: [coluna('NOVO', [lead])] })
    leadsService.estatisticas.mockResolvedValue({ data: {} })
    const tela = montar(KanbanView)
    await flushPromises()

    await tela.findComponent({ name: 'KanbanBoard' }).vm.$emit('mover', {
      lead,
      estagio: 'FECHADO_PERDIDO',
    })
    await flushPromises()

    expect(tela.text()).toContain('Por que perdemos este lead?')
    expect(leadsService.mover).not.toHaveBeenCalled()
  })

  it('move direto quando o estágio não é perda', async () => {
    const lead = { id: 'l1', nome: 'Fernanda', estagio: 'NOVO' }
    leadsService.funil.mockResolvedValue({ data: [coluna('NOVO', [lead])] })
    leadsService.estatisticas.mockResolvedValue({ data: {} })
    leadsService.mover.mockResolvedValue({ data: {} })
    const tela = montar(KanbanView)
    await flushPromises()

    await tela
      .findComponent({ name: 'KanbanBoard' })
      .vm.$emit('mover', { lead, estagio: 'QUALIFICADO' })
    await flushPromises()

    expect(leadsService.mover).toHaveBeenCalledWith('l1', { estagio: 'QUALIFICADO' })
  })
})

describe('CobrancasView', () => {
  const cobranca = {
    id: 'c1',
    contrato_numero: 'LOC-2026-0001',
    inquilino: 'Paulo',
    competencia: '2026-08-01',
    vencimento: '2026-08-10',
    status: 'ABERTA',
    status_display: 'Aberta',
    valor_total: '3100.00',
    dias_de_atraso: 5,
  }

  it('exibe inadimplência e dias de atraso', async () => {
    cobrancasService.listar.mockResolvedValue(pagina([cobranca]))
    cobrancasService.inadimplencia.mockResolvedValue({
      data: { percentual: 33.3, atrasadas: 1, total_cobrancas: 3 },
    })
    const tela = montar(CobrancasView)
    await flushPromises()

    expect(tela.text()).toContain('33.3%')
    expect(tela.text()).toContain('(5d)')
  })

  it('abre o diálogo de baixa já com o valor da cobrança', async () => {
    cobrancasService.listar.mockResolvedValue(pagina([cobranca]))
    cobrancasService.inadimplencia.mockResolvedValue({ data: { percentual: 0 } })
    const tela = montar(CobrancasView)
    await flushPromises()

    const botao = tela.findAll('button').find((b) => b.text() === 'Dar baixa')
    await botao.trigger('click')

    expect(tela.text()).toContain('Registrar recebimento')
    expect(tela.find('dialog').exists()).toBe(true)
  })
})

describe('RepassesView', () => {
  it('mostra a composição do repasse', async () => {
    repassesService.listar.mockResolvedValue(
      pagina([
        {
          id: 'r1',
          contrato_numero: 'LOC-2026-0001',
          proprietario: 'Helena',
          competencia: '2026-08-01',
          valor_bruto: '2500.00',
          taxa_administracao: '200.00',
          valor_liquido: '2300.00',
          status: 'PENDENTE',
          status_display: 'Pendente',
        },
      ]),
    )
    const tela = montar(RepassesView)
    await flushPromises()

    expect(tela.text()).toContain('Helena')
    expect(tela.text()).toContain('2.300,00')
  })

  it('explica o vazio quando nada foi recebido ainda', async () => {
    repassesService.listar.mockResolvedValue(pagina([]))
    const tela = montar(RepassesView)
    await flushPromises()

    expect(tela.text()).toContain('Nenhum repasse ainda')
  })
})

describe('ComissoesView', () => {
  it('lista comissões com status', async () => {
    comissoesService.listar.mockResolvedValue(
      pagina([
        {
          id: 'k1',
          contrato_numero: 'VEN-2026-0001',
          usuario_nome: 'Carla',
          papel_display: 'Captador',
          percentual_snapshot: '40.00',
          valor: '12000.00',
          status: 'PREVISTA',
          status_display: 'Prevista',
        },
      ]),
    )
    const tela = montar(ComissoesView)
    await flushPromises()

    expect(tela.text()).toContain('Carla')
    expect(tela.text()).toContain('12.000,00')
  })
})

describe('ContratosListView', () => {
  it('sinaliza contrato próximo do vencimento', async () => {
    contratosService.listar.mockResolvedValue(
      pagina([
        {
          id: 'ct1',
          numero: 'LOC-2026-0001',
          imovel_codigo: 'REF-000001',
          tipo: 'LOCACAO',
          tipo_display: 'Locação',
          status: 'ATIVO',
          status_display: 'Ativo',
          data_inicio: '2026-01-10',
          data_fim: '2026-10-10',
          valor: '2500.00',
          dias_para_vencer: 45,
        },
      ]),
    )
    const tela = montar(ContratosListView)
    await flushPromises()

    expect(tela.text()).toContain('LOC-2026-0001')
    expect(tela.text()).toContain('(45 dias)')
  })
})

describe('PessoasView', () => {
  it('formata documento e telefone na listagem', async () => {
    pessoasService.listar.mockResolvedValue(
      pagina([
        {
          id: 'p1',
          nome: 'Helena Martins',
          cpf_cnpj: '52998224725',
          tipo_display: 'Pessoa física',
          telefone: '35998880001',
          email: 'helena@cliente.test',
        },
      ]),
    )
    const tela = montar(PessoasView)
    await flushPromises()

    expect(tela.text()).toContain('529.982.247-25')
    expect(tela.text()).toContain('(35) 99888-0001')
  })

  it('abre o formulário de nova pessoa', async () => {
    pessoasService.listar.mockResolvedValue(pagina([]))
    const tela = montar(PessoasView)
    await flushPromises()

    const botao = tela.findAll('button').find((b) => b.text() === 'Nova pessoa')
    await botao.trigger('click')

    expect(tela.text()).toContain('Nova pessoa')
    expect(tela.find('dialog').exists()).toBe(true)
  })
})

describe('AgendaView', () => {
  it('lista as visitas do dia com horário', async () => {
    visitasService.agenda.mockResolvedValue({
      data: [
        {
          id: 'v1',
          lead_nome: 'Fernanda',
          imovel_codigo: 'REF-000001',
          imovel_titulo: 'Apartamento',
          agendada_para: '2026-08-20T14:30:00-03:00',
          realizada: false,
          atrasada: false,
        },
      ],
    })
    const tela = montar(AgendaView)
    await flushPromises()

    expect(tela.text()).toContain('Fernanda')
    expect(tela.text()).toContain('14:30')
  })

  it('mostra estado vazio quando não há visita', async () => {
    visitasService.agenda.mockResolvedValue({ data: [] })
    const tela = montar(AgendaView)
    await flushPromises()

    expect(tela.text()).toContain('Nenhuma visita neste dia')
  })
})

describe('VistoriasListView', () => {
  it('destaca itens com avaria', async () => {
    vistoriasService.listar.mockResolvedValue(
      pagina([
        {
          id: 'vi1',
          contrato_numero: 'LOC-2026-0001',
          imovel_codigo: 'REF-000001',
          tipo_display: 'Entrada',
          realizada_em: '2026-08-10',
          total_itens: 40,
          itens_com_problema: 3,
          status: 'FINALIZADA',
          status_display: 'Finalizada',
        },
      ]),
    )
    const tela = montar(VistoriasListView)
    await flushPromises()

    expect(tela.text()).toContain('(3 com avaria)')
  })
})

describe('RelatoriosView', () => {
  it('mostra DRE, margem e desempenho', async () => {
    financeiroService.relatorio.mockImplementation((nome) => {
      if (nome === 'dre') {
        return Promise.resolve({
          data: {
            receita_operacional: '5000.00',
            despesa_operacional: '2000.00',
            resultado: '3000.00',
            margem_percentual: 60,
            volume_movimentado: '20000.00',
            por_categoria: { RECEITA: { 'Taxa de administração': '5000.00' } },
          },
        })
      }
      if (nome === 'fluxo') return Promise.resolve({ data: [] })
      return Promise.resolve({
        data: [
          {
            corretor: 'Carla',
            leads: 4,
            ganhos: 1,
            conversao: 25,
            imoveis_captados: 2,
            comissao_prevista: '1000.00',
          },
        ],
      })
    })
    leadsService.estatisticas.mockResolvedValue({
      data: { por_origem: { Site: 3 }, por_motivo_perda: { PRECO: 1 } },
    })
    const tela = montar(RelatoriosView)
    await flushPromises()

    expect(tela.text()).toContain('margem 60%')
    expect(tela.text()).toContain('Carla')
    expect(tela.text()).toContain('25%')
  })
})
