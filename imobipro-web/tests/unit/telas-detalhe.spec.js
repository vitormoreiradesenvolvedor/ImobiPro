import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  comissoesService,
  contratosService,
  imoveisService,
  integracoesService,
  leadsService,
  pessoasService,
  usuariosService,
  vistoriasService,
} from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import ConfiguracoesView from '@/views/configuracoes/ConfiguracoesView.vue'
import ContratoDetalheView from '@/views/contratos/ContratoDetalheView.vue'
import ContratoFormView from '@/views/contratos/ContratoFormView.vue'
import LeadDetalheView from '@/views/crm/LeadDetalheView.vue'
import DashboardView from '@/views/dashboard/DashboardView.vue'
import ImovelDetalheView from '@/views/imoveis/ImovelDetalheView.vue'
import ImovelFormView from '@/views/imoveis/ImovelFormView.vue'
import CadastroView from '@/views/auth/CadastroView.vue'
import LoginView from '@/views/auth/LoginView.vue'
import VistoriaExecucaoView from '@/views/vistorias/VistoriaExecucaoView.vue'

vi.mock('@/services/api')

const push = vi.fn()

function montar(componente, { params = {}, papel = 'ADMIN', permissoes = {} } = {}) {
  const tela = mount(componente, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false })],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
      mocks: {
        $route: { params, query: {} },
        $router: { push, back: vi.fn() },
      },
    },
  })

  const auth = useAuthStore()
  auth.usuario = { nome_completo: 'Ana Ribeiro', papel, papel_display: papel, email: 'a@b.c' }
  auth.tenant = { razao_social: 'Horizonte Imóveis', nome_fantasia: 'Horizonte' }
  auth.permissoes = {
    ver_financeiro: true,
    ver_crm: true,
    gerenciar_usuarios: true,
    ...permissoes,
  }
  return tela
}

// vue-router injeta useRoute/useRouter por provide; nos testes, o mock global.
vi.mock('vue-router', async () => {
  const real = await vi.importActual('vue-router')
  return {
    ...real,
    useRoute: () => ({ params: { id: 'x1' }, query: {} }),
    useRouter: () => ({ push, back: vi.fn() }),
  }
})

const IMOVEL = {
  id: 'i1',
  codigo: 'REF-000001',
  titulo: 'Apartamento no Centro',
  descricao: 'Reformado.',
  situacao: 'EM_CAPTACAO',
  situacao_display: 'Em captação',
  publicado_site: false,
  valor_locacao: '2500.00',
  valor_condominio: '480.00',
  valor_iptu_mensal: '120.00',
  quartos: 2,
  suites: 0,
  banheiros: 1,
  vagas: 1,
  area_util: '68.00',
  mobiliado: false,
  aceita_pet: true,
  matricula: '12345',
  endereco: {
    logradouro: 'Rua A',
    numero: '10',
    bairro: 'Centro',
    cidade: 'Lavras',
    uf: 'MG',
  },
  proprietario_detalhe: { nome: 'Helena', cpf_cnpj: '52998224725', telefone: '' },
  captador_nome: 'Carla',
  caracteristicas_detalhe: [{ id: 'c1', nome: 'Piscina' }],
  fotos: [],
  pendencias_publicacao: ['Mínimo de 5 fotos (tem 0).'],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LoginView', () => {
  it('mostra o erro devolvido pela store', async () => {
    const tela = montar(LoginView)
    const auth = useAuthStore()
    auth.erro = 'Credenciais inválidas.'
    await flushPromises()

    expect(tela.text()).toContain('Credenciais inválidas.')
  })

  it('envia e-mail e senha ao submeter', async () => {
    const tela = montar(LoginView)
    const auth = useAuthStore()
    auth.login = vi.fn().mockResolvedValue(true)

    await tela.find('input[type="email"]').setValue('admin@horizonteimoveis.com.br')
    await tela.find('input[type="password"]').setValue('segredo')
    await tela.find('form').trigger('submit')

    expect(auth.login).toHaveBeenCalledWith('admin@horizonteimoveis.com.br', 'segredo')
  })
})

describe('CadastroView', () => {
  async function preencher(tela, senha = 'casa-nova-2026!', confirmacao = senha) {
    const campos = tela.findAll('input')
    const valores = [
      'Serra Verde Imóveis Ltda',
      'Serra Verde',
      '12.345.678/0001-90',
      null,
      'Marina Costa',
      'marina@serraverde.com.br',
      '',
      senha,
      confirmacao,
    ]
    for (const [i, valor] of valores.entries()) {
      if (valor !== null) await campos[i].setValue(valor)
    }
  }

  it('sugere o endereço do site a partir do nome fantasia', async () => {
    const tela = montar(CadastroView)
    await preencher(tela)

    expect(tela.findAll('input')[3].element.value).toBe('serra-verde')
  })

  it('envia os dados sem a confirmação e vai ao painel', async () => {
    const tela = montar(CadastroView)
    const auth = useAuthStore()
    auth.cadastrar = vi.fn().mockResolvedValue(true)
    push.mockClear()

    await preencher(tela)
    await tela.find('form').trigger('submit')
    await flushPromises()

    const enviado = auth.cadastrar.mock.calls[0][0]
    expect(enviado).toMatchObject({
      subdominio: 'serra-verde',
      email: 'marina@serraverde.com.br',
    })
    expect(enviado).not.toHaveProperty('confirmacao')
    expect(push).toHaveBeenCalledWith({ name: 'dashboard' })
  })

  it('não envia quando as senhas não conferem', async () => {
    const tela = montar(CadastroView)
    const auth = useAuthStore()
    auth.cadastrar = vi.fn()

    await preencher(tela, 'casa-nova-2026!', 'outra-senha-123')
    await tela.find('form').trigger('submit')

    expect(auth.cadastrar).not.toHaveBeenCalled()
    expect(tela.text()).toContain('As senhas não conferem.')
  })

  it('mostra o erro de cada campo devolvido pela API', async () => {
    const tela = montar(CadastroView)
    const auth = useAuthStore()
    auth.errosCampos = { email: ['Já existe uma conta com este e-mail.'] }
    await flushPromises()

    expect(tela.text()).toContain('Já existe uma conta com este e-mail.')
  })
})

describe('ImovelDetalheView', () => {
  it('lista pendências que impedem a publicação', async () => {
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    imoveisService.historico.mockResolvedValue({ data: [] })
    const tela = montar(ImovelDetalheView)
    await flushPromises()

    expect(tela.text()).toContain('Pendências para publicar')
    expect(tela.text()).toContain('Mínimo de 5 fotos')
  })

  it('mostra valores e características na aba de dados', async () => {
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    imoveisService.historico.mockResolvedValue({ data: [] })
    const tela = montar(ImovelDetalheView)
    await flushPromises()

    expect(tela.text()).toContain('2.500,00')
    expect(tela.text()).toContain('Piscina')
  })

  it('troca para a aba de histórico', async () => {
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    imoveisService.historico.mockResolvedValue({
      data: [
        {
          id: 'h1',
          tipo_display: 'Cadastro',
          descricao: 'Imóvel cadastrado.',
          criado_em: '2026-08-18T10:00:00Z',
        },
      ],
    })
    const tela = montar(ImovelDetalheView)
    await flushPromises()

    const aba = tela.findAll('button').find((b) => b.text() === 'Histórico')
    await aba.trigger('click')

    expect(tela.text()).toContain('Imóvel cadastrado.')
  })

  it('esconde ações de edição para o papel financeiro', async () => {
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    imoveisService.historico.mockResolvedValue({ data: [] })
    const tela = montar(ImovelDetalheView, { papel: 'FINANCEIRO' })
    await flushPromises()

    expect(tela.findAll('button').some((b) => b.text() === 'Publicar')).toBe(false)
  })
})

describe('ImovelFormView', () => {
  it('avança e volta pelos passos do wizard', async () => {
    pessoasService.listar.mockResolvedValue({ data: { results: [] } })
    imoveisService.caracteristicas.mockResolvedValue({ data: [] })
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    const tela = montar(ImovelFormView)
    await flushPromises()

    expect(tela.text()).toContain('Passo 1 de 5')

    const continuar = tela.findAll('button').find((b) => b.text() === 'Continuar')
    await continuar.trigger('click')
    expect(tela.text()).toContain('Passo 2 de 5')

    const voltar = tela.findAll('button').find((b) => b.text() === 'Voltar')
    await voltar.trigger('click')
    expect(tela.text()).toContain('Passo 1 de 5')
  })

  it('busca o endereço pelo CEP', async () => {
    pessoasService.listar.mockResolvedValue({ data: { results: [] } })
    imoveisService.caracteristicas.mockResolvedValue({ data: [] })
    imoveisService.obter.mockResolvedValue({ data: IMOVEL })
    pessoasService.consultarCep.mockResolvedValue({
      data: { logradouro: 'Praça Central', bairro: 'Centro', cidade: 'Lavras', uf: 'MG' },
    })
    const tela = montar(ImovelFormView)
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Continuar')
      .trigger('click')

    const rotulos = tela.findAll('label')
    const idCep = rotulos.find((l) => l.text().includes('CEP')).attributes('for')
    const cep = tela.find(`#${idCep}`)
    await cep.setValue('37200000')
    await flushPromises()
    await cep.trigger('blur')
    await flushPromises()

    expect(pessoasService.consultarCep).toHaveBeenCalledWith('37200000')
  })
})

describe('LeadDetalheView', () => {
  const LEAD = {
    id: 'l1',
    nome: 'Fernanda Rocha',
    email: 'fe@cliente.test',
    telefone: '35991112222',
    estagio: 'NOVO',
    estagio_display: 'Novo',
    origem_display: 'Site próprio',
    temperatura: 'QUENTE',
    valor_estimado: '350000.00',
    corretor_nome: 'Carla',
    sla_estourado: true,
    sla_cumprido: null,
    primeiro_contato_em: null,
    interacoes: [],
    imovel_detalhe: null,
    mensagem: 'Quero visitar.',
  }

  it('mostra o alerta de SLA estourado', async () => {
    leadsService.obter.mockResolvedValue({ data: LEAD })
    const tela = montar(LeadDetalheView)
    await flushPromises()

    expect(tela.text()).toContain('SLA estourado')
    expect(tela.text()).toContain('aguardando')
  })

  it('registra interação e recarrega o lead', async () => {
    leadsService.obter.mockResolvedValue({ data: LEAD })
    leadsService.registrarInteracao.mockResolvedValue({ data: {} })
    const tela = montar(LeadDetalheView)
    await flushPromises()

    await tela.find('textarea').setValue('Cliente atendeu.')
    await flushPromises()
    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(leadsService.registrarInteracao).toHaveBeenCalledWith('l1', {
      tipo: 'LIGACAO',
      descricao: 'Cliente atendeu.',
    })
  })

  it('não envia interação em branco', async () => {
    leadsService.obter.mockResolvedValue({ data: LEAD })
    const tela = montar(LeadDetalheView)
    await flushPromises()

    await tela.find('form').trigger('submit')

    expect(leadsService.registrarInteracao).not.toHaveBeenCalled()
  })
})

describe('ContratoDetalheView', () => {
  const CONTRATO = {
    id: 'ct1',
    numero: 'LOC-2026-0001',
    tipo: 'LOCACAO',
    tipo_display: 'Locação',
    status: 'RASCUNHO',
    status_display: 'Rascunho',
    imovel_codigo: 'REF-000001',
    imovel_titulo: 'Apartamento',
    data_inicio: '2026-08-01',
    data_fim: '2029-01-01',
    valor: '2500.00',
    dia_vencimento: 10,
    taxa_administracao_percent: '8.00',
    partes: [],
    reajustes: [],
    comissoes: [],
    pendencias_ativacao: ['Contrato sem locador.'],
  }

  it('mostra pendências de ativação do rascunho', async () => {
    contratosService.obter.mockResolvedValue({ data: CONTRATO })
    const tela = montar(ContratoDetalheView)
    await flushPromises()

    expect(tela.text()).toContain('Pendências para ativar')
    expect(tela.text()).toContain('Contrato sem locador.')
  })

  it('ativa o contrato pelo botão', async () => {
    contratosService.obter.mockResolvedValue({ data: CONTRATO })
    contratosService.ativar.mockResolvedValue({
      data: { ...CONTRATO, status: 'ATIVO', status_display: 'Ativo', pendencias_ativacao: [] },
    })
    const tela = montar(ContratoDetalheView)
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Ativar contrato')
      .trigger('click')
    await flushPromises()

    expect(contratosService.ativar).toHaveBeenCalledWith('ct1')
    expect(tela.text()).toContain('Ativo')
  })

  it('calcula a prévia do reajuste antes de aplicar', async () => {
    const ativo = {
      ...CONTRATO,
      status: 'ATIVO',
      status_display: 'Ativo',
      pendencias_ativacao: [],
    }
    contratosService.obter.mockResolvedValue({ data: ativo })
    contratosService.previaReajuste.mockResolvedValue({
      data: {
        valor_anterior: '2500.00',
        valor_novo: '2625.00',
        diferenca: '125.00',
        percentual: '5.000',
      },
    })
    const tela = montar(ContratoDetalheView)
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Reajustar')
      .trigger('click')
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Calcular prévia')
      .trigger('click')
    await flushPromises()

    expect(tela.text()).toContain('2.625,00')
    expect(contratosService.aplicarReajuste).not.toHaveBeenCalled()
  })

  it('aceita percentual digitado com vírgula na prévia', async () => {
    const ativo = {
      ...CONTRATO,
      status: 'ATIVO',
      status_display: 'Ativo',
      pendencias_ativacao: [],
    }
    contratosService.obter.mockResolvedValue({ data: ativo })
    contratosService.previaReajuste.mockResolvedValue({
      data: {
        valor_anterior: '2500.00',
        valor_novo: '2612.50',
        diferenca: '112.50',
        percentual: '4.500',
      },
    })
    const tela = montar(ContratoDetalheView)
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Reajustar')
      .trigger('click')
    const rotulo = tela
      .findAll('label')
      .find((l) => l.text().startsWith('Percentual do índice'))
    await tela.find(`#${rotulo.attributes('for')}`).setValue('4,5')
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Calcular prévia')
      .trigger('click')
    await flushPromises()

    expect(contratosService.previaReajuste).toHaveBeenCalledWith('ct1', '4.5')
  })
})

describe('ContratoFormView', () => {
  it('manda o percentual com ponto quando o usuário digita com vírgula', async () => {
    imoveisService.listar.mockResolvedValue({ data: { results: [] } })
    pessoasService.listar.mockResolvedValue({ data: { results: [] } })
    contratosService.criar.mockResolvedValue({ data: { id: 'ct9' } })
    const tela = montar(ContratoFormView)
    await flushPromises()

    const taxa = tela.findAll('label').find((l) => l.text().startsWith('Taxa de administração'))
    const campo = tela.find(`#${taxa.attributes('for')}`)
    await campo.setValue('10,5')
    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(contratosService.criar).toHaveBeenCalled()
    expect(contratosService.criar.mock.calls[0][0].taxa_administracao_percent).toBe('10.5')
  })

  it('exibe condições de locação e permite adicionar parte', async () => {
    imoveisService.listar.mockResolvedValue({ data: { results: [] } })
    pessoasService.listar.mockResolvedValue({ data: { results: [] } })
    const tela = montar(ContratoFormView)
    await flushPromises()

    expect(tela.text()).toContain('Condições da locação')

    const antes = tela.findAll('select').length
    await tela
      .findAll('button')
      .find((b) => b.text() === 'Adicionar parte')
      .trigger('click')

    expect(tela.findAll('select').length).toBeGreaterThan(antes)
  })
})

describe('VistoriaExecucaoView', () => {
  const VISTORIA = {
    id: 'vi1',
    tipo: 'ENTRADA',
    tipo_display: 'Entrada',
    status: 'RASCUNHO',
    status_display: 'Em preenchimento',
    contrato_numero: 'LOC-2026-0001',
    imovel_codigo: 'REF-000001',
    realizada_em: '2026-08-18',
    total_itens: 2,
    itens_com_problema: 1,
    assinatura_locatario: false,
    assinatura_imobiliaria: false,
    itens: [
      { id: 'it1', comodo: 'Sala', item: 'Piso', estado: 'BOM', observacao: '', fotos: [] },
      {
        id: 'it2',
        comodo: 'Sala',
        item: 'Parede',
        estado: 'RUIM',
        observacao: 'mancha',
        fotos: [],
      },
    ],
  }

  it('agrupa itens por cômodo', async () => {
    vistoriasService.obter.mockResolvedValue({ data: VISTORIA })
    const tela = montar(VistoriaExecucaoView)
    await flushPromises()

    expect(tela.text()).toContain('Sala')
    expect(tela.text()).toContain('1 com apontamento')
  })

  it('registra o estado escolhido para o item', async () => {
    vistoriasService.obter.mockResolvedValue({ data: VISTORIA })
    vistoriasService.registrarItem.mockResolvedValue({ data: { fotos: [] } })
    const tela = montar(VistoriaExecucaoView)
    await flushPromises()

    const botao = tela.findAll('button').find((b) => b.text() === 'Ótimo')
    await botao.trigger('click')
    await flushPromises()

    expect(vistoriasService.registrarItem).toHaveBeenCalledWith(
      'vi1',
      expect.objectContaining({ comodo: 'Sala', item: 'Piso', estado: 'OTIMO' }),
    )
  })

  it('bloqueia edição quando a vistoria está finalizada', async () => {
    vistoriasService.obter.mockResolvedValue({
      data: { ...VISTORIA, status: 'FINALIZADA', status_display: 'Finalizada' },
    })
    const tela = montar(VistoriaExecucaoView)
    await flushPromises()

    const botao = tela.findAll('button').find((b) => b.text() === 'Ótimo')
    expect(botao.element.disabled).toBe(true)
  })
})

describe('ConfiguracoesView', () => {
  beforeEach(() => {
    usuariosService.listar.mockResolvedValue({
      data: {
        results: [
          {
            id: 'u1',
            nome_completo: 'Ana',
            email: 'a@b.c',
            papel_display: 'Admin',
            ativo: true,
          },
        ],
      },
    })
    comissoesService.configuracao.mockResolvedValue({
      data: {
        percentual_venda: '6.00',
        rateio_captador: '40.00',
        rateio_vendedor: '40.00',
        rateio_imobiliaria: '20.00',
      },
    })
    integracoesService.listar.mockResolvedValue({
      data: { results: [{ id: 'in1', portal_display: 'Viva Real', url_webhook: '/api/x' }] },
    })
    integracoesService.eventos.mockResolvedValue({ data: { results: [] } })
  })

  it('lista a equipe da imobiliária', async () => {
    const tela = montar(ConfiguracoesView)
    await flushPromises()

    expect(tela.text()).toContain('Ana')
  })

  it('impede salvar rateio que não soma 100%', async () => {
    const tela = montar(ConfiguracoesView)
    await flushPromises()

    const aba = tela.findAll('button').find((b) => b.text() === 'Tabela de comissão')
    await aba.trigger('click')

    const campos = tela.findAll('input')
    await campos[1].setValue('50')
    await flushPromises()

    expect(tela.text()).toContain('precisa ser exatamente 100%')
    const salvar = tela.findAll('button').find((b) => b.text() === 'Salvar tabela')
    expect(salvar.element.disabled).toBe(true)
  })

  it('salva a tabela de comissão convertendo a vírgula em ponto', async () => {
    comissoesService.salvarConfiguracao.mockResolvedValue({ data: {} })
    const tela = montar(ConfiguracoesView)
    await flushPromises()

    await tela
      .findAll('button')
      .find((b) => b.text() === 'Tabela de comissão')
      .trigger('click')
    const venda = tela.findAll('label').find((l) => l.text().startsWith('Comissão de venda'))
    await tela.find(`#${venda.attributes('for')}`).setValue('6,5')
    await tela.find('form').trigger('submit')
    await flushPromises()

    expect(comissoesService.salvarConfiguracao).toHaveBeenCalledWith(
      expect.objectContaining({ percentual_venda: '6.5' }),
    )
  })

  it('mostra a URL de webhook de cada portal', async () => {
    const tela = montar(ConfiguracoesView)
    await flushPromises()

    const aba = tela.findAll('button').find((b) => b.text() === 'Integrações')
    await aba.trigger('click')

    expect(tela.text()).toContain('Viva Real')
    expect(tela.text()).toContain('/api/x')
  })
})

describe('DashboardView', () => {
  it('mostra indicadores e o bloco do dia', async () => {
    const { financeiroService, cobrancasService, visitasService } =
      await import('@/services/api')
    imoveisService.estatisticas.mockResolvedValue({
      data: { carteira_venda: '1000000.00', total_geral: 8, publicados: 6, por_bairro: {} },
    })
    leadsService.estatisticas.mockResolvedValue({
      data: {
        abertos: 9,
        taxa_conversao: 50,
        sla_cumprido_percentual: 80,
        tempo_medio_primeiro_contato_min: 6,
        por_estagio: { Novo: 3 },
      },
    })
    financeiroService.resumo.mockResolvedValue({
      data: {
        resultado_do_mes: '3000.00',
        receita_do_mes: '5000.00',
        a_receber: '9000.00',
        a_receber_vencido: '1000.00',
        inadimplencia: { percentual: 12.5, atrasadas: 1 },
      },
    })
    visitasService.agenda.mockResolvedValue({ data: [] })
    leadsService.listar.mockResolvedValue({ data: { results: [] } })
    cobrancasService.listar.mockResolvedValue({ data: { results: [] } })

    const tela = montar(DashboardView)
    await flushPromises()

    expect(tela.text()).toContain('Precisa de você hoje')
    expect(tela.text()).toContain('12.5%')
    expect(tela.text()).toContain('Nenhum lead esperando')
  })

  it('não quebra quando o papel não tem acesso ao financeiro', async () => {
    const { financeiroService, cobrancasService, visitasService } =
      await import('@/services/api')
    imoveisService.estatisticas.mockResolvedValue({
      data: { carteira_venda: '0', total_geral: 0, publicados: 0, por_bairro: {} },
    })
    leadsService.estatisticas.mockResolvedValue({ data: { abertos: 0, taxa_conversao: 0 } })
    financeiroService.resumo.mockRejectedValue({ response: { status: 403 } })
    visitasService.agenda.mockResolvedValue({ data: [] })
    leadsService.listar.mockResolvedValue({ data: { results: [] } })
    cobrancasService.listar.mockResolvedValue({ data: { results: [] } })

    const tela = montar(DashboardView, { papel: 'CORRETOR' })
    await flushPromises()

    expect(tela.text()).toContain('Leads abertos')
    expect(tela.text()).not.toContain('Inadimplência')
  })
})
