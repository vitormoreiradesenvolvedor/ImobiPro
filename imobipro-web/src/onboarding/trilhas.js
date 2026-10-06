/**
 * Roteiros guiados (product tours).
 *
 * Cada passo aponta para um elemento real da tela por `alvo` (seletor CSS). O
 * overlay escurece o resto, recorta o alvo e mostra o balão ao lado. Quando o
 * passo tem `exigeClique`, o usuário só avança clicando no próprio elemento
 * é o "faça você mesmo" do onboarding.
 *
 * `rota` leva o usuário até a tela antes de procurar o alvo.
 */

export const TOURS = {
  'primeiros-passos': {
    titulo: 'Como o ImobiPro funciona',
    descricao: 'Um giro de 1 minuto pelo painel.',
    passos: [
      {
        rota: '/',
        alvo: '[data-tour="menu-lateral"]',
        titulo: 'O menu segue o fluxo do negócio',
        texto:
          'De cima para baixo: primeiro a carteira (imóveis e pessoas), depois o ' +
          'comercial (funil, agenda, contratos) e por fim a administração ' +
          '(dinheiro, vistorias e relatórios). O que seu papel não pode ver nem aparece.',
        posicao: 'direita',
      },
      {
        rota: '/',
        alvo: '[data-tour="kpis"]',
        titulo: 'O painel responde "quanto entra este mês"',
        texto:
          'Resultado, a receber, inadimplência e carteira à venda. Enquanto não ' +
          'houver movimento real, os números ficam zerados nada aqui é inventado.',
        posicao: 'baixo',
      },
      {
        rota: '/',
        alvo: '[data-tour="precisa-hoje"]',
        titulo: 'Comece o dia por aqui',
        texto:
          'Leads sem primeiro contato, visitas do dia e cobranças em atraso. ' +
          'É a lista do que trava dinheiro se ficar parado.',
        posicao: 'cima',
      },
      {
        rota: '/',
        alvo: '[data-tour="ver-site"]',
        titulo: 'Este botão abre o site que o cliente vê',
        texto:
          'É a mesma vitrine que aparece para quem procura imóvel: catálogo por ' +
          'categoria, ficha com mapa e pedido de visita sem cadastro. Abre em ' +
          'outra aba, então o painel continua aqui.',
        posicao: 'baixo',
      },
      {
        rota: '/',
        alvo: '[data-tour="botao-tutorial"]',
        titulo: 'O guia fica sempre aqui',
        texto:
          'Este botão abre as missões e reabre qualquer tutorial. Pode fechar ' +
          'agora e voltar quando quiser.',
        posicao: 'baixo',
      },
    ],
  },

  'captar-imovel': {
    titulo: 'Captar um imóvel',
    descricao: 'Do proprietário até o anúncio publicado.',
    passos: [
      {
        rota: '/pessoas',
        alvo: '[data-tour="nova-pessoa"]',
        titulo: 'Primeiro o dono, depois o imóvel',
        texto:
          'Todo imóvel exige um proprietário cadastrado. O CPF/CNPJ é conferido ' +
          'por dígito verificador e o CEP preenche o endereço sozinho.',
        posicao: 'esquerda',
        exigeClique: true,
      },
      {
        rota: '/imoveis',
        alvo: '[data-tour="captar-imovel"]',
        titulo: 'Agora o imóvel',
        texto:
          'O cadastro é um assistente de 5 passos: identificação, endereço, ' +
          'características, valores e documentação. O código REF é gerado sozinho.',
        posicao: 'esquerda',
        exigeClique: true,
      },
      {
        rota: '/imoveis/novo',
        alvo: '[data-tour="progresso-wizard"]',
        titulo: 'Você pode ir e voltar',
        texto:
          'Nada se perde entre os passos. No passo de endereço, preencha latitude ' +
          'e longitude: sem elas o imóvel não entra no mapa nem pode ser publicado.',
        posicao: 'baixo',
      },
      {
        rota: '/imoveis',
        alvo: '[data-tour="filtros-imoveis"]',
        titulo: 'Buscar como o cliente pergunta',
        texto:
          'Busca por texto usa índice do banco (aceita "cobertura mobiliada"). ' +
          'Dá para filtrar por tipo, finalidade, situação e número de quartos.',
        posicao: 'baixo',
      },
      {
        rota: '/imoveis',
        alvo: '[data-tour="modos-visualizacao"]',
        titulo: 'Cards, tabela ou mapa',
        texto:
          'O mapa mostra só imóveis geocodificados e é o melhor jeito de ' +
          'responder "o que você tem neste bairro?".',
        posicao: 'baixo',
      },
    ],
  },

  'funil-de-vendas': {
    titulo: 'Trabalhar o funil',
    descricao: 'Lead, SLA de 15 minutos, visita e proposta.',
    passos: [
      {
        rota: '/crm',
        alvo: '[data-tour="metricas-funil"]',
        titulo: 'Três números que importam',
        texto:
          'Leads abertos, taxa de conversão e SLA cumprido. O SLA é o diferencial ' +
          'do produto: 15 minutos para o primeiro contato.',
        posicao: 'baixo',
      },
      {
        rota: '/crm',
        alvo: '[data-tour="novo-lead"]',
        titulo: 'Lead entra por aqui ou sozinho',
        texto:
          'Você pode cadastrar na mão, mas leads do site e dos portais entram ' +
          'automaticamente e já saem distribuídos para um corretor ativo.',
        posicao: 'esquerda',
      },
      {
        rota: '/crm',
        alvo: '[data-tour="kanban"]',
        titulo: 'Arraste o cartão para mover o lead',
        texto:
          'Cartão com borda vermelha piscando é SLA estourado. Ao arrastar para ' +
          '"perdido", o sistema exige o motivo é ele que alimenta o relatório de perdas.',
        posicao: 'cima',
      },
    ],
  },

  'fechar-contrato': {
    titulo: 'Fechar um contrato',
    descricao: 'Rascunho, ativação, comissão e cobranças.',
    passos: [
      {
        rota: '/contratos',
        alvo: '[data-tour="novo-contrato"]',
        titulo: 'Todo contrato nasce rascunho',
        texto:
          'Rascunho pode ser editado à vontade. Locação exige locador, locatário ' +
          'e data de término.',
        posicao: 'esquerda',
      },
      {
        rota: '/contratos',
        alvo: '[data-tour="filtros-contratos"]',
        titulo: 'Acompanhe o que vence',
        texto:
          'Filtre por "vencendo em 90 dias" para renegociar antes da hora. O ' +
          'sistema também avisa em 90, 60 e 30 dias.',
        posicao: 'baixo',
      },
    ],
  },

  'rodar-financeiro': {
    titulo: 'Rodar o financeiro',
    descricao: 'Receber, repassar e prestar contas.',
    permissao: 'ver_financeiro',
    passos: [
      {
        rota: '/financeiro/receber',
        alvo: '[data-tour="inadimplencia"]',
        titulo: 'Inadimplência do mês em um número',
        texto:
          'As cobranças nascem sozinhas 10 dias antes do vencimento. Atrasou, a ' +
          'régua dispara lembrete, cobrança, aviso formal e jurídico.',
        posicao: 'baixo',
      },
      {
        rota: '/financeiro/receber',
        alvo: '[data-tour="conciliar"]',
        titulo: 'Baixa em lote pelo banco',
        texto:
          'Suba o arquivo de retorno (CNAB) e o sistema baixa tudo que casar, ' +
          'listando o que não encontrou em vez de adivinhar.',
        posicao: 'esquerda',
      },
      {
        rota: '/financeiro/pagar',
        alvo: '[data-tour="tabela-repasses"]',
        titulo: 'O que é do proprietário',
        texto:
          'Aluguel menos taxa de administração e retenções. Condomínio e IPTU não ' +
          'entram: são de terceiros. O extrato em PDF sai daqui.',
        posicao: 'cima',
      },
    ],
  },
}

/** Tours disponíveis para o papel do usuário. */
export function toursDisponiveis(pode) {
  return Object.entries(TOURS)
    .filter(([, tour]) => !tour.permissao || pode(tour.permissao))
    .map(([id, tour]) => ({ id, ...tour, total: tour.passos.length }))
}
