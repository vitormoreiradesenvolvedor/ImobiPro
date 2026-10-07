import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import BarrasHorizontais from '@/components/charts/BarrasHorizontais.vue'
import ColunasMensais from '@/components/charts/ColunasMensais.vue'
import KanbanBoard from '@/components/crm/KanbanBoard.vue'
import KanbanCard from '@/components/crm/KanbanCard.vue'
import TimelineLead from '@/components/crm/TimelineLead.vue'
import ImovelCard from '@/components/imoveis/ImovelCard.vue'
import { moeda } from '@/utils/formatters'

const routerStub = {
  global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
}

const IMOVEL = {
  id: 'i1',
  codigo: 'REF-000001',
  titulo: 'Apartamento no Centro',
  finalidade: 'LOCACAO',
  situacao: 'DISPONIVEL',
  situacao_display: 'Disponível',
  valor_locacao: '2500.00',
  valor_condominio: '480.00',
  quartos: 2,
  banheiros: 1,
  vagas: 1,
  area_util: '68.00',
  bairro: 'Centro',
  cidade: 'Lavras',
  publicado_site: true,
  foto_capa: null,
}

const lead = (extras = {}) => ({
  id: 'l1',
  nome: 'Fernanda Rocha',
  estagio: 'NOVO',
  temperatura: 'QUENTE',
  origem_display: 'Site próprio',
  valor_estimado: '350000.00',
  corretor_nome: 'Carla Dias',
  primeiro_contato_em: null,
  minutos_para_sla: 8,
  sla_estourado: false,
  ...extras,
})

describe('ImovelCard', () => {
  it('mostra o valor de locação com sufixo mensal', () => {
    const tela = mount(ImovelCard, { props: { imovel: IMOVEL }, ...routerStub })

    expect(tela.text()).toContain(moeda('2500.00'))
    expect(tela.text()).toContain('/mês')
    expect(tela.text()).toContain('REF-000001')
  })

  it('mostra o valor de venda sem sufixo', () => {
    const venda = { ...IMOVEL, finalidade: 'VENDA', valor_venda: '890000.00' }
    const tela = mount(ImovelCard, { props: { imovel: venda }, ...routerStub })

    expect(tela.text()).toContain(moeda('890000.00'))
    expect(tela.text()).not.toContain('/mês')
  })

  it('sinaliza que está publicado no site', () => {
    const tela = mount(ImovelCard, { props: { imovel: IMOVEL }, ...routerStub })

    expect(tela.text()).toContain('no site')
  })
})

describe('KanbanCard', () => {
  it('avisa quando o SLA está perto de estourar', () => {
    const tela = mount(KanbanCard, {
      props: { lead: lead({ minutos_para_sla: 3 }) },
      ...routerStub,
    })

    expect(tela.text()).toContain('para o 1º contato')
    expect(tela.classes().join(' ')).toContain('amber')
  })

  it('pinta de vermelho o SLA já estourado', () => {
    const tela = mount(KanbanCard, {
      props: { lead: lead({ minutos_para_sla: -12, sla_estourado: true }) },
      ...routerStub,
    })

    expect(tela.text()).toContain('SLA estourado')
    expect(tela.classes().join(' ')).toContain('red')
  })

  it('some com o alerta depois do primeiro contato', () => {
    const tela = mount(KanbanCard, {
      props: { lead: lead({ primeiro_contato_em: '2026-08-18T10:00:00Z' }) },
      ...routerStub,
    })

    expect(tela.text()).not.toContain('SLA')
    expect(tela.text()).toContain('Carla Dias')
  })
})

describe('KanbanBoard', () => {
  const colunas = [
    { estagio: 'NOVO', rotulo: 'Novo', total: 1, valor_total: '350000.00', leads: [lead()] },
    { estagio: 'PROPOSTA', rotulo: 'Proposta', total: 0, valor_total: '0', leads: [] },
  ]

  it('mostra total e valor por coluna', () => {
    const tela = mount(KanbanBoard, { props: { colunas }, ...routerStub })

    expect(tela.text()).toContain('Novo')
    expect(tela.text()).toContain(moeda('350000.00'))
  })

  it('convida a arrastar quando a coluna está vazia', () => {
    const tela = mount(KanbanBoard, { props: { colunas }, ...routerStub })

    expect(tela.text()).toContain('Arraste um lead para cá')
  })

  it('emite o movimento ao soltar em outra coluna', async () => {
    const tela = mount(KanbanBoard, { props: { colunas }, ...routerStub })

    await tela.findAll('[draggable="true"]')[0].trigger('dragstart')
    await tela.findAll('section')[1].trigger('drop')

    expect(tela.emitted('mover')[0][0].estagio).toBe('PROPOSTA')
  })

  it('ignora soltar na mesma coluna de origem', async () => {
    const tela = mount(KanbanBoard, { props: { colunas }, ...routerStub })

    await tela.findAll('[draggable="true"]')[0].trigger('dragstart')
    await tela.findAll('section')[0].trigger('drop')

    expect(tela.emitted('mover')).toBeUndefined()
  })
})

describe('TimelineLead', () => {
  it('lista interações com autor e tipo', () => {
    const tela = mount(TimelineLead, {
      props: {
        interacoes: [
          {
            id: 1,
            tipo: 'LIGACAO',
            tipo_display: 'Ligação',
            descricao: 'Cliente atendeu.',
            usuario_nome: 'Carla',
            criado_em: '2026-08-18T12:00:00Z',
          },
        ],
      },
    })

    expect(tela.text()).toContain('Ligação')
    expect(tela.text()).toContain('Cliente atendeu.')
    expect(tela.text()).toContain('Carla')
  })

  it('explica o vazio em vez de mostrar lista em branco', () => {
    const tela = mount(TimelineLead, { props: { interacoes: [] } })

    expect(tela.text()).toContain('Nenhuma interação registrada')
  })
})

describe('gráficos', () => {
  it('barras ordenam do maior para o menor e respeitam o limite', () => {
    const tela = mount(BarrasHorizontais, {
      props: { dados: { Centro: 3, 'Vila Ester': 9, Aquenta: 1 }, limite: 2 },
    })

    const linhas = tela.findAll('li')
    expect(linhas).toHaveLength(2)
    expect(linhas[0].text()).toContain('Vila Ester')
  })

  it('barras avisam quando não há dado', () => {
    const tela = mount(BarrasHorizontais, { props: { dados: {} } })

    expect(tela.text()).toContain('Sem dados no período')
  })

  it('colunas mensais desenham receita e despesa', () => {
    const tela = mount(ColunasMensais, {
      props: {
        serie: [
          { mes: '2026-07', receita: 1000, despesa: 400 },
          { mes: '2026-08', receita: 2000, despesa: 900 },
        ],
      },
    })

    expect(tela.text()).toContain('Receita')
    expect(tela.text()).toContain('Despesa')
    expect(tela.findAll('.bg-marca').length).toBeGreaterThan(0)
  })

  it('colunas mensais avisam quando não houve movimento', () => {
    const tela = mount(ColunasMensais, { props: { serie: [] } })

    expect(tela.text()).toContain('Sem movimento registrado')
  })
})
