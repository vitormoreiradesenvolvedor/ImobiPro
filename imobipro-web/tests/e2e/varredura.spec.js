/**
 * Varredura completa: percorre todas as telas e todos os fluxos pela interface,
 * do jeito que o usuário faz sem atalho por API para criar dado.
 *
 * A suíte é encadeada de propósito: o imóvel captado no começo é o mesmo que
 * entra no contrato, gera cobrança, repasse e vistoria no fim. É assim que se
 * descobre integração quebrada entre módulos.
 *
 * Cada etapa deixa um screenshot em `tests/e2e/telas/varredura/`.
 */

import { expect, request as apiRequest, test } from '@playwright/test'

import { autenticar, PNG_MINIMO, reativarGuia, zerarOperacao } from './apoio.js'

const ADMIN = { email: 'admin@horizonteimoveis.com.br', senha: 'horizonte-2026' }
const TELAS = 'tests/e2e/telas/varredura'
const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080'

const PROPRIETARIO = { nome: 'Helena Duarte Proprietária', cpf: '529.982.247-25' }
const INQUILINO = { nome: 'Rafael Nunes Inquilino', cpf: '168.995.350-09' }
const IMOVEL = { titulo: 'Apartamento 302 no Centro' }

test.describe.configure({ mode: 'serial' })

let pagina
let codigoDoImovel
let numeroDoContrato
/** Erros de JavaScript não tratados: qualquer um derruba a varredura no fim. */
const errosDeJs = []

async function foto(nome) {
  await pagina.screenshot({ path: `${TELAS}/${nome}.png` })
}

/** Espera o toast de sucesso é o sinal de que a API aceitou, não o de tela. */
async function confirmou(texto) {
  await expect(pagina.getByText(texto).first()).toBeVisible({ timeout: 15000 })
}

async function irPara(rotulo, tituloEsperado) {
  await pagina.getByRole('link', { name: rotulo }).click()
  await expect(pagina.getByRole('heading', { level: 1 })).toContainText(tituloEsperado)
}

async function fecharTourSeAberto() {
  const sair = pagina.getByRole('button', { name: 'Sair do tutorial' })
  if (await sair.isVisible().catch(() => false)) {
    await sair.click()
    await expect(pagina.getByRole('dialog', { name: 'Tutorial guiado' })).toHaveCount(0)
  }
}

async function abrirGuia() {
  await pagina.getByRole('button', { name: /Tutorial/ }).click()
  await expect(pagina.getByRole('complementary', { name: 'Guia de uso' })).toBeVisible()
}

async function fecharGuia() {
  await pagina
    .getByRole('button', { name: 'Fechar guia' })
    .click()
    .catch(async () => {
      await pagina.keyboard.press('Escape')
    })
  await expect(pagina.getByRole('complementary', { name: 'Guia de uso' })).toHaveCount(0)
}

test.beforeAll(async ({ browser, baseURL }) => {
  zerarOperacao()
  // O guia é por usuário e sobrevive à limpeza da operação: reabre do zero para
  // a varredura ver o tutorial de boas-vindas como um usuário novo veria.
  const api = await apiRequest.newContext()
  await reativarGuia(api, baseURL)
  await api.dispose()

  pagina = await browser.newPage()
  pagina.on('pageerror', (erro) => errosDeJs.push(String(erro)))
})

test.afterAll(async () => {
  await pagina?.close()

  // A varredura cria um usuário por execução; sem isso a equipe cresce sem parar.
  const api = await apiRequest.newContext()
  const { Authorization } = await autenticar(api, BASE)
  const equipe = await api.get(`${BASE}/api/v1/auth/usuarios/?search=bruno.`, {
    headers: { Authorization },
  })
  for (const pessoa of (await equipe.json()).results ?? []) {
    if (pessoa.email?.startsWith('bruno.')) {
      await api.delete(`${BASE}/api/v1/auth/usuarios/${pessoa.id}/`, {
        headers: { Authorization },
      })
    }
  }
  await api.dispose()
})

test.describe('varredura completa pela interface', () => {
  test('01 · login e painel com a base zerada', async () => {
    await pagina.goto('/login')
    await foto('01-login')

    await pagina.getByLabel('E-mail').fill(ADMIN.email)
    await pagina.getByLabel('Senha').fill(ADMIN.senha)
    await pagina.getByRole('button', { name: 'Entrar' }).click()

    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá', {
      timeout: 15000,
    })
    // Tutorial de boas-vindas abre sozinho no primeiro acesso.
    await expect(pagina.getByRole('dialog', { name: 'Tutorial guiado' })).toContainText(
      'Passo 1 de 5',
    )
    await foto('02-tour-abre-sozinho')
  })

  test('02 · tutorial "Como o ImobiPro funciona" do começo ao fim', async () => {
    const balao = pagina.getByRole('dialog', { name: 'Tutorial guiado' })

    await expect(balao).toContainText('O menu segue o fluxo do negócio')
    await pagina.getByRole('button', { name: 'Próximo' }).click()

    await expect(balao).toContainText('Passo 2 de 5')
    await expect(balao).toContainText('quanto entra este mês')
    await foto('03-tour-passo-2')

    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Passo 3 de 5')
    await expect(balao).toContainText('Comece o dia por aqui')

    // Voltar preserva o roteiro.
    await pagina.getByRole('button', { name: 'Voltar' }).click()
    await expect(balao).toContainText('Passo 2 de 5')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await pagina.getByRole('button', { name: 'Próximo' }).click()

    // O tutorial mostra onde fica o site que o cliente enxerga.
    await expect(balao).toContainText('Passo 4 de 5')
    await expect(balao).toContainText('site que o cliente vê')
    await expect(pagina.locator('[data-tour="ver-site"]')).toHaveAttribute(
      'href',
      '/site/horizonte',
    )
    await pagina.getByRole('button', { name: 'Próximo' }).click()

    await expect(balao).toContainText('Passo 5 de 5')
    await expect(pagina.getByRole('button', { name: 'Concluir' })).toBeVisible()
    await foto('04-tour-ultimo-passo')
    await pagina.getByRole('button', { name: 'Concluir' }).click()

    await expect(pagina.getByRole('dialog', { name: 'Tutorial guiado' })).toHaveCount(0)

    // Concluído não reabre sozinho.
    await pagina.reload()
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá')
    await pagina.waitForTimeout(1500)
    await expect(pagina.getByRole('dialog', { name: 'Tutorial guiado' })).toHaveCount(0)
  })

  test('03 · painel do guia lista missões, trilhas e nível', async () => {
    await abrirGuia()
    const painel = pagina.getByRole('complementary', { name: 'Guia de uso' })

    await expect(painel).toContainText('Começando')
    await expect(painel).toContainText('0 de 12 missões concluídas')
    await expect(painel).toContainText('Montar a carteira')
    await expect(painel).toContainText('Vender e alugar')
    await expect(painel).toContainText('Fechar contratos')
    await expect(painel).toContainText('Rodar o financeiro')
    await expect(painel).toContainText('Proteger o imóvel')
    await foto('05-painel-missoes')
    await fecharGuia()
  })

  test('04 · cadastra proprietário e inquilino', async () => {
    await irPara('Pessoas', 'Pessoas')
    await expect(pagina.getByText('Nenhuma pessoa cadastrada')).toBeVisible()
    await foto('06-pessoas-vazio')

    for (const pessoa of [PROPRIETARIO, INQUILINO]) {
      await pagina.getByRole('button', { name: 'Nova pessoa' }).first().click()
      await pagina.getByLabel('Nome / Razão social').fill(pessoa.nome)
      await pagina.getByLabel('CPF/CNPJ').fill(pessoa.cpf)
      await pagina.getByLabel('E-mail').fill(`${pessoa.cpf.replace(/\D/g, '')}@teste.local`)
      await pagina.getByLabel('Telefone').fill('35991234567')
      await pagina.getByRole('button', { name: 'Salvar' }).click()
      await confirmou('Cadastro salvo.')
    }

    await expect(pagina.getByText(PROPRIETARIO.nome)).toBeVisible()
    await expect(pagina.getByText(INQUILINO.nome)).toBeVisible()
    await foto('07-pessoas-cadastradas')
  })

  test('04b · foto do cadastro é opcional, entra e sai', async () => {
    await pagina.getByRole('row', { name: new RegExp(PROPRIETARIO.nome) }).click()

    // Sem foto o cadastro salva normalmente: o rótulo é de adicionar, não de trocar.
    const escolher = pagina.getByText('Adicionar foto')
    await expect(escolher).toBeVisible()

    await pagina
      .locator('input[type="file"]')
      .setInputFiles({ name: 'retrato.png', mimeType: 'image/png', buffer: PNG_MINIMO })
    await pagina.getByRole('button', { name: 'Salvar' }).click()
    await confirmou('Cadastro salvo.')

    await pagina.getByRole('row', { name: new RegExp(PROPRIETARIO.nome) }).click()
    await expect(pagina.getByText('Trocar foto')).toBeVisible()
    await foto('07b-pessoa-com-foto')

    await pagina.getByRole('button', { name: 'remover' }).click()
    await confirmou('Foto removida.')
    await expect(pagina.getByText('Adicionar foto')).toBeVisible()
    await pagina.getByRole('button', { name: 'Cancelar' }).click()
  })

  test('05 · CEP preenche o endereço sozinho', async () => {
    await pagina.getByRole('row', { name: new RegExp(PROPRIETARIO.nome) }).click()
    await pagina.getByLabel('CEP').fill('37200-066')
    await pagina.getByLabel('CEP').blur()

    await expect(pagina.getByLabel('Cidade')).toHaveValue(/Lavras/i, { timeout: 15000 })
    await expect(pagina.getByLabel('UF')).toHaveValue('MG')
    await foto('08-cep-preenchido')

    await pagina.getByRole('button', { name: 'Salvar' }).click()
    await confirmou('Cadastro salvo.')
  })

  test('06 · missão de cadastro é reconhecida sem recarregar', async () => {
    await expect(pagina.getByRole('button', { name: /Tutorial/ })).toContainText('11')
    await abrirGuia()
    await expect(pagina.getByRole('complementary', { name: 'Guia de uso' })).toContainText(
      '1 de 12 missões concluídas',
    )
    await foto('09-missao-cumprida')
    await fecharGuia()
  })

  test('07 · tutorial "Captar um imóvel" só avança com o clique real', async () => {
    await abrirGuia()
    await pagina
      .getByRole('listitem')
      .filter({ hasText: 'Captar um imóvel' })
      .getByRole('button')
      .click()

    const balao = pagina.getByRole('dialog', { name: 'Tutorial guiado' })

    // Passo 1: o tutorial leva para /pessoas e trava até clicar em "Nova pessoa".
    await expect(pagina).toHaveURL(/\/pessoas/)
    await expect(balao).toContainText('Primeiro o dono, depois o imóvel')
    await expect(balao).toContainText('Clique no botão destacado')
    await expect(pagina.getByRole('button', { name: 'Próximo' })).toHaveCount(0)
    await foto('10-tour-exige-clique')

    await pagina.getByRole('button', { name: 'Nova pessoa' }).first().click()
    await expect(balao).toContainText('Passo 2 de 5')

    // Passo 2: mesma regra, agora em /imoveis.
    await expect(pagina).toHaveURL(/\/imoveis/)
    await expect(balao).toContainText('Agora o imóvel')
    // Há dois "Captar imóvel" (topo e estado vazio); o tour aponta para o do topo.
    await pagina.locator('[data-tour="captar-imovel"]').click()

    await expect(pagina).toHaveURL(/\/imoveis\/novo/)
    await expect(balao).toContainText('Passo 3 de 5')
    await expect(balao).toContainText('Você pode ir e voltar')
    await foto('11-tour-no-assistente')

    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Buscar como o cliente pergunta')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Cards, tabela ou mapa')
    await pagina.getByRole('button', { name: 'Concluir' }).click()

    await expect(pagina.getByRole('dialog', { name: 'Tutorial guiado' })).toHaveCount(0)
  })

  test('07b · "Voltar" no primeiro passo da captação sai para a lista', async () => {
    await pagina.goto('/imoveis/novo')
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Captar imóvel')

    await pagina.getByRole('button', { name: 'Voltar' }).click()

    await expect(pagina).toHaveURL(/\/imoveis$/)
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Imóveis')
  })

  test('08 · captação completa no assistente de 5 passos', async () => {
    await pagina.goto('/imoveis/novo')
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Captar imóvel')

    // 1 · Identificação
    await pagina.getByLabel('Título do anúncio').fill(IMOVEL.titulo)
    await pagina
      .getByLabel('Descrição')
      .fill('Apartamento reformado, dois quartos, vaga coberta e sol da manhã.')
    await pagina.getByLabel('Tipo').selectOption('APARTAMENTO')
    await pagina.getByLabel('Finalidade').selectOption('LOCACAO')
    // A opção mostra "Nome CPF": casa pelo começo do rótulo.
    const opcaoDono = pagina
      .getByLabel('Proprietário')
      .locator('option', { hasText: PROPRIETARIO.nome })
    await pagina.getByLabel('Proprietário').selectOption(await opcaoDono.getAttribute('value'))
    await foto('12-wizard-identificacao')
    await pagina.getByRole('button', { name: 'Continuar' }).click()

    // 2 · Endereço, com CEP e coordenadas (sem elas não publica)
    await expect(pagina.getByText('Passo 2 de 5')).toBeVisible()
    await pagina.getByLabel('CEP').fill('37200-066')
    await pagina.getByLabel('CEP').blur()
    await expect(pagina.getByLabel('Cidade')).toHaveValue(/Lavras/i, { timeout: 15000 })
    await pagina.getByLabel('Número').fill('302')
    if (!(await pagina.getByLabel('Logradouro').inputValue())) {
      await pagina.getByLabel('Logradouro').fill('Rua Central')
    }
    if (!(await pagina.getByLabel('Bairro').inputValue())) {
      await pagina.getByLabel('Bairro').fill('Centro')
    }
    await pagina.getByLabel('Latitude').fill('-21.245')
    await pagina.getByLabel('Longitude').fill('-44.997')
    await foto('13-wizard-endereco')
    await pagina.getByRole('button', { name: 'Continuar' }).click()

    // 3 · Características
    await expect(pagina.getByText('Passo 3 de 5')).toBeVisible()
    await pagina.getByLabel('Quartos', { exact: true }).fill('2')
    await pagina.getByLabel('Suítes').fill('1')
    await pagina.getByLabel('Banheiros').fill('2')
    await pagina.getByLabel('Vagas').fill('1')
    await pagina.getByLabel('Área total (m²)').fill('78')
    await pagina.getByLabel('Área útil (m²)').fill('68')
    await pagina.getByLabel('Ano de construção').fill('2015')
    // "Mobiliado" existe como campo do imóvel e como característica do catálogo.
    await pagina.getByLabel('Mobiliado', { exact: true }).first().check()
    await foto('14-wizard-caracteristicas')
    await pagina.getByRole('button', { name: 'Continuar' }).click()

    // 4 · Valores
    await expect(pagina.getByText('Passo 4 de 5')).toBeVisible()
    await pagina.getByLabel('Valor de locação').fill('2500,00')
    await pagina.getByLabel('Condomínio mensal').fill('480,00')
    await pagina.getByLabel('IPTU anual').fill('1200,00')
    await foto('15-wizard-valores')
    await pagina.getByRole('button', { name: 'Continuar' }).click()

    // 5 · Documentação
    await expect(pagina.getByText('Passo 5 de 5')).toBeVisible()
    await pagina.getByLabel('Matrícula').fill('MAT-45231')
    await pagina.getByLabel('Autorização de venda assinada').check()
    await foto('16-wizard-documentacao')
    await pagina.getByRole('button', { name: 'Salvar imóvel' }).click()

    await expect(pagina).toHaveURL(/\/imoveis\/[0-9a-f-]{36}$/, { timeout: 15000 })
    const texto = await pagina
      .getByText(/REF-\d{6}/)
      .first()
      .innerText()
    codigoDoImovel = /REF-\d{6}/.exec(texto)[0]
    expect(codigoDoImovel).toBe('REF-000001')
    await foto('17-ficha-do-imovel')
  })

  test('09 · publicação exige as cinco fotos', async () => {
    await pagina.getByRole('button', { name: 'Publicar' }).click()
    await expect(pagina.getByText(/foto/i).first()).toBeVisible()
    await foto('18-publicacao-barrada')

    await pagina.getByRole('button', { name: 'Fotos e mídia' }).click()
    await pagina.locator('input[type="file"]').setInputFiles(
      Array.from({ length: 5 }, (_, indice) => ({
        name: `foto-${indice}.png`,
        mimeType: 'image/png',
        buffer: PNG_MINIMO,
      })),
    )
    await confirmou('5 foto(s) enviada(s).')
    await expect(pagina.getByText('capa').first()).toBeVisible()
    await foto('19-galeria-com-capa')

    await pagina.getByRole('button', { name: 'Publicar' }).click()
    await expect(pagina.getByRole('button', { name: 'Despublicar' })).toBeVisible({
      timeout: 15000,
    })
    await foto('20-imovel-publicado')
  })

  test('10 · histórico registra a publicação', async () => {
    await pagina.getByRole('button', { name: 'Histórico' }).click()
    await expect(pagina.getByText(/[Pp]ublica/).first()).toBeVisible()
    await foto('21-historico')
  })

  test('11 · listagem: busca, filtros e os três modos de visualização', async () => {
    await irPara('Imóveis', 'Imóveis')
    await expect(pagina.getByText(IMOVEL.titulo)).toBeVisible()

    await pagina.getByLabel('Buscar').fill('apartamento reformado')
    await expect(pagina.getByText(IMOVEL.titulo)).toBeVisible({ timeout: 15000 })
    await foto('22-busca-textual')

    await pagina.getByLabel('Buscar').fill('')
    await pagina.getByLabel('Finalidade').selectOption('VENDA')
    await expect(pagina.getByText('Nenhum imóvel encontrado')).toBeVisible({ timeout: 15000 })
    await foto('23-filtro-sem-resultado')

    await pagina.getByLabel('Finalidade').selectOption('')
    await expect(pagina.getByText(IMOVEL.titulo)).toBeVisible()

    const modos = { Tabela: '24', Mapa: '25', Cards: '26' }
    for (const [modo, numero] of Object.entries(modos)) {
      await pagina.getByRole('button', { name: modo }).click()
      await pagina.waitForTimeout(600)
      await foto(`${numero}-modo-${modo.toLowerCase()}`)
    }
  })

  test('12 · tutorial "Trabalhar o funil"', async () => {
    await abrirGuia()
    await pagina
      .getByRole('listitem')
      .filter({ hasText: 'Trabalhar o funil' })
      .getByRole('button')
      .click()

    const balao = pagina.getByRole('dialog', { name: 'Tutorial guiado' })
    await expect(pagina).toHaveURL(/\/crm/)
    await expect(balao).toContainText('Três números que importam')
    await foto('27-tour-funil')

    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Lead entra por aqui')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Arraste o cartão para mover o lead')
    await pagina.getByRole('button', { name: 'Concluir' }).click()
    await expect(balao).toHaveCount(0)
    // Concluir o tutorial deixa o usuário onde ele estava não o joga de volta.
    await expect(pagina).toHaveURL(/\/crm/)
  })

  test('13 · cria lead e move no kanban arrastando', async () => {
    await pagina.getByRole('button', { name: 'Novo lead' }).click()
    await pagina.getByLabel('Nome').fill('Marina Prospect')
    await pagina.getByLabel('Telefone').fill('35998887766')
    await pagina.getByLabel('E-mail').fill('marina.prospect@teste.local')
    // SITE e PORTAL só entram por integração: o cadastro manual não os oferece.
    await pagina.getByLabel('Origem').selectOption('INDICACAO')
    await pagina.getByLabel('Valor estimado').fill('2500,00')
    await pagina.getByRole('button', { name: 'Cadastrar' }).click()

    const cartao = pagina.getByText('Marina Prospect').first()
    await expect(cartao).toBeVisible({ timeout: 15000 })
    await foto('28-kanban-com-lead')

    // Arrasta de "Novo" para "Em contato" drag nativo do HTML.
    const destino = pagina.locator('section', { hasText: 'Em contato' }).first()
    await cartao.dragTo(destino)
    await confirmou('Marina Prospect movido.')
    await foto('29-kanban-lead-movido')
  })

  test('14 · ficha do lead: interação, visita e proposta', async () => {
    await pagina.getByText('Marina Prospect').first().click()
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Marina Prospect')

    await pagina.getByLabel('O que aconteceu').fill('Ligação atendida, cliente quer visitar.')
    await pagina.getByRole('button', { name: 'Registrar', exact: true }).click()
    await confirmou('Interação registrada.')
    await expect(pagina.getByText('cliente quer visitar')).toBeVisible()
    await foto('30-lead-timeline')

    await pagina.getByRole('button', { name: 'Agendar visita' }).click()
    const daquiADias = new Date(Date.now() + 2 * 24 * 3600 * 1000)
    const quando = `${daquiADias.toISOString().slice(0, 10)}T10:00`
    await pagina.getByLabel('Imóvel').selectOption({ index: 1 })
    await pagina.getByLabel('Data e hora').fill(quando)
    await pagina.getByRole('button', { name: 'Agendar', exact: true }).click()
    await confirmou('Visita agendada.')
    await foto('31-visita-agendada')

    await pagina.getByRole('button', { name: 'Nova proposta' }).click()
    await pagina.getByLabel('Imóvel').selectOption({ index: 1 })
    await pagina.getByLabel('Valor ofertado').fill('2400,00')
    await pagina.getByLabel('Condições de pagamento').fill('Entrada mais 12 parcelas.')
    const validade = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString().slice(0, 10)
    await pagina.getByLabel('Validade').fill(validade)
    await pagina.getByRole('button', { name: 'Registrar proposta' }).click()
    await confirmou('Proposta registrada.')
    await foto('32-proposta-registrada')
  })

  test('15 · agenda mostra a visita marcada', async () => {
    await irPara('Agenda', 'Agenda')
    const daquiADias = new Date(Date.now() + 2 * 24 * 3600 * 1000)
    await pagina.getByLabel('Dia').fill(daquiADias.toISOString().slice(0, 10))
    await expect(pagina.getByText('Marina Prospect').first()).toBeVisible({ timeout: 15000 })
    await foto('33-agenda')
  })

  test('16 · tutorial "Fechar um contrato"', async () => {
    await abrirGuia()
    await pagina
      .getByRole('listitem')
      .filter({ hasText: 'Fechar um contrato' })
      .getByRole('button')
      .click()

    const balao = pagina.getByRole('dialog', { name: 'Tutorial guiado' })
    await expect(pagina).toHaveURL(/\/contratos/)
    await expect(balao).toContainText('Todo contrato nasce rascunho')
    await foto('34-tour-contratos')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Acompanhe o que vence')
    await pagina.getByRole('button', { name: 'Concluir' }).click()
    await expect(balao).toHaveCount(0)
  })

  test('17 · rascunho de locação com locador e locatário', async () => {
    // Dois botões "Novo contrato" (topo e estado vazio): usa o do topo.
    await pagina.locator('[data-tour="novo-contrato"]').click()
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('contrato')

    await pagina.getByLabel('Tipo').selectOption('LOCACAO')
    await pagina.getByLabel('Imóvel').selectOption({ index: 1 })

    const hoje = new Date()
    const daqui12Meses = new Date(hoje.getFullYear() + 1, hoje.getMonth(), hoje.getDate())
    await pagina.getByLabel('Início').fill(hoje.toISOString().slice(0, 10))
    await pagina.getByLabel('Término').fill(daqui12Meses.toISOString().slice(0, 10))
    await pagina
      .getByLabel(/^Valor/)
      .first()
      .fill('2500,00')
    await pagina.getByLabel('Dia de vencimento').fill('10')
    await pagina.getByLabel('Taxa de administração (%)').fill('10')
    await pagina.getByLabel('Garantia', { exact: true }).selectOption('CAUCAO')
    await pagina.getByLabel('Valor da garantia').fill('7500,00')

    // Locação exige locador e locatário é a validação de ativação.
    await pagina.getByRole('button', { name: 'Adicionar parte' }).click()
    const donoLocador = pagina.getByLabel('Pessoa').first()
    await donoLocador.selectOption(
      await donoLocador.locator('option', { hasText: PROPRIETARIO.nome }).getAttribute('value'),
    )
    await pagina.getByLabel('Papel').first().selectOption('LOCADOR')

    await pagina.getByRole('button', { name: 'Adicionar parte' }).click()
    const locatario = pagina.getByLabel('Pessoa').nth(1)
    await locatario.selectOption(
      await locatario.locator('option', { hasText: INQUILINO.nome }).getAttribute('value'),
    )
    await pagina.getByLabel('Papel').nth(1).selectOption('LOCATARIO')
    await foto('35-contrato-rascunho')

    await pagina.getByRole('button', { name: 'Criar rascunho' }).click()
    await expect(pagina).toHaveURL(/\/contratos\/[0-9a-f-]{36}$/, { timeout: 15000 })
    await expect(pagina.getByText(/Rascunho/i).first()).toBeVisible()
    numeroDoContrato = /LOC-\d{4}-\d{4}/.exec(
      await pagina.getByRole('heading', { level: 1 }).innerText(),
    )[0]
    await foto('36-contrato-criado')
  })

  test('18 · ativação tira o imóvel do mercado e gera comissão e cobranças', async () => {
    await pagina.getByRole('button', { name: 'Ativar contrato' }).click()
    await expect(pagina.getByText(/Ativo/i).first()).toBeVisible({ timeout: 15000 })
    await foto('37-contrato-ativo')

    // Comissão nasce na assinatura e aparece sem recarregar a tela.
    const cartaoComissoes = pagina.locator('section,div').filter({ hasText: 'Comissões' })
    await expect(cartaoComissoes.getByText('Geradas na ativação do contrato.')).toHaveCount(0)
    await expect(pagina.getByText(/Imobiliária|Captador|Vendedor/).first()).toBeVisible()
    await foto('37a-comissoes-do-contrato')

    // Prévia de reajuste não altera nada só simula.
    await pagina.getByRole('button', { name: 'Reajustar' }).click()
    await pagina.getByLabel('Percentual do índice (%)').fill('4,5')
    await pagina.getByRole('button', { name: 'Calcular prévia' }).click()
    await expect(pagina.getByText(/2\.6\d\d,\d\d/).first()).toBeVisible({ timeout: 15000 })
    await foto('37b-previa-reajuste')
    await pagina.getByRole('button', { name: 'Cancelar' }).click()
  })

  test('19 · imóvel do contrato aparece como locado', async () => {
    await irPara('Imóveis', 'Imóveis')
    // "Locado" também existe como opção do filtro: olha o selo do card.
    await pagina.getByLabel('Situação').selectOption('LOCADO')
    await expect(pagina.getByText(IMOVEL.titulo)).toBeVisible({ timeout: 15000 })
    await expect(pagina.getByText('Locado', { exact: true }).last()).toBeVisible()
    await foto('38-imovel-locado')
  })

  test('20 · contas a receber: baixa de uma cobrança', async () => {
    await irPara('Contas a receber', 'Contas a receber')
    // A listagem identifica pela cobrança do contrato, não pelo código do imóvel.
    await expect(pagina.getByText(numeroDoContrato).first()).toBeVisible({ timeout: 15000 })
    await foto('39-cobrancas')

    await pagina.getByRole('button', { name: 'Dar baixa' }).first().click()
    await expect(pagina.getByText('Registrar recebimento')).toBeVisible()
    await pagina.getByLabel('Data do pagamento').fill(new Date().toISOString().slice(0, 10))
    await pagina.getByRole('button', { name: 'Confirmar baixa' }).click()
    await confirmou('Baixa registrada. Repasse gerado para o proprietário.')
    await foto('40-cobranca-baixada')
  })

  test('21 · tutorial "Rodar o financeiro"', async () => {
    await abrirGuia()
    await pagina
      .getByRole('listitem')
      .filter({ hasText: 'Rodar o financeiro' })
      .getByRole('button')
      .first()
      .click()

    const balao = pagina.getByRole('dialog', { name: 'Tutorial guiado' })
    await expect(balao).toContainText('Inadimplência do mês em um número')
    await foto('41-tour-financeiro')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(balao).toContainText('Baixa em lote pelo banco')
    await pagina.getByRole('button', { name: 'Próximo' }).click()
    await expect(pagina).toHaveURL(/\/financeiro\/pagar/)
    await expect(balao).toContainText('O que é do proprietário')
    await pagina.getByRole('button', { name: /Concluir|Próximo/ }).click()
    await expect(balao).toHaveCount(0)
  })

  test('22 · repasse ao proprietário com retenção e extrato', async () => {
    await irPara('Repasses', 'Repasses')
    await expect(pagina.getByText(PROPRIETARIO.nome).first()).toBeVisible({ timeout: 15000 })
    await foto('42-repasses')

    await pagina.getByRole('button', { name: 'Reter' }).first().click()
    await pagina.getByLabel('Descrição').fill('Conserto do chuveiro')
    await pagina
      .getByLabel(/^Valor/)
      .first()
      .fill('150,00')
    await pagina.getByRole('button', { name: 'Aplicar retenção' }).click()
    await confirmou('Retenção aplicada ao repasse.')
    // Retenção sai do líquido: 2.250 − 150.
    await expect(pagina.getByText('R$ 2.100,00').first()).toBeVisible({ timeout: 15000 })
    await foto('43-retencao')

    await pagina.getByRole('button', { name: 'Liquidar' }).first().click()
    await pagina.getByRole('button', { name: 'Liquidar' }).last().click()
    await confirmou('Repasse liquidado e lançado no financeiro.')
    await foto('44-repasse-liquidado')
  })

  test('23 · conciliação por arquivo de retorno do banco (CNAB 400)', async () => {
    await irPara('Contas a receber', 'Contas a receber')

    // Monta um retorno de verdade a partir do "nosso número" de uma cobrança aberta.
    const api = await apiRequest.newContext()
    const { Authorization } = await autenticar(api, BASE)
    const lista = await api.get(`${BASE}/api/v1/cobrancas/?status=ABERTA`, {
      headers: { Authorization },
    })
    const cobranca = (await lista.json()).results[0]
    await api.dispose()

    const centavos = String(Math.round(Number(cobranca.valor_total) * 100)).padStart(13, '0')
    const hoje = new Date()
    const ddmmaa =
      String(hoje.getDate()).padStart(2, '0') +
      String(hoje.getMonth() + 1).padStart(2, '0') +
      String(hoje.getFullYear()).slice(2)

    const linha = '1'.padEnd(400, ' ').split('')
    const escrever = (inicio, texto) => {
      for (let i = 0; i < texto.length; i += 1) linha[inicio + i] = texto[i]
    }
    escrever(62, String(cobranca.nosso_numero).padStart(11, '0'))
    escrever(108, '06')
    escrever(110, ddmmaa)
    escrever(253, centavos)

    await pagina.locator('[data-tour="conciliar"] input[type="file"]').setInputFiles({
      name: 'retorno.ret',
      mimeType: 'text/plain',
      buffer: Buffer.from(`${linha.join('')}\n`, 'utf8'),
    })

    await confirmou('1 cobrança(s) baixada(s).')
    await foto('45-conciliacao-cnab')
  })

  test('24 · comissões do contrato assinado aparecem na tela', async () => {
    await irPara('Comissões', 'Comissões')
    await expect(pagina.getByText(numeroDoContrato).first()).toBeVisible({ timeout: 15000 })
    await foto('46-comissoes')
  })

  test('25 · vistoria de entrada: checklist, observação e laudo', async () => {
    await irPara('Contratos', 'Contratos')
    await pagina.getByRole('row', { name: new RegExp(numeroDoContrato) }).click()
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText(numeroDoContrato)
    await pagina.getByRole('button', { name: 'Vistoria de entrada' }).click()

    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Vistoria', {
      timeout: 15000,
    })
    await expect(pagina.getByText('Sala')).toBeVisible()
    await foto('47-vistoria-checklist')

    // Marca o estado de alguns itens é o que alimenta o comparativo de saída.
    // O retorno visual é o próprio botão ficar pressionado, sem toast.
    const otimo = pagina.getByRole('button', { name: 'Ótimo' }).first()
    await otimo.click()
    await expect(otimo).toHaveAttribute('aria-pressed', 'true', { timeout: 15000 })

    const regular = pagina.getByRole('button', { name: 'Regular' }).nth(1)
    await regular.click()
    await expect(regular).toHaveAttribute('aria-pressed', 'true')
    await foto('48-vistoria-itens')

    await pagina.getByRole('button', { name: 'Finalizar vistoria' }).click()
    await confirmou('Vistoria finalizada. Laudo disponível em PDF.')
    await expect(pagina.getByText('Finalizada')).toBeVisible()

    // Assinatura das duas partes é o que fecha o laudo.
    await pagina.getByRole('button', { name: 'Assinar (locatário)' }).click()
    await confirmou('Assinatura registrada.')
    await pagina.getByRole('button', { name: 'Assinar (imobiliária)' }).click()
    await foto('49-vistoria-finalizada')
  })

  test('26 · laudo e contrato saem em PDF de verdade', async () => {
    const api = await apiRequest.newContext()
    const { Authorization } = await autenticar(api, BASE)

    const contratos = await api.get(`${BASE}/api/v1/contratos/`, { headers: { Authorization } })
    const contrato = (await contratos.json()).results[0]
    const pdfContrato = await api.get(`${BASE}/api/v1/contratos/${contrato.id}/pdf/`, {
      headers: { Authorization },
    })
    expect(pdfContrato.status()).toBe(200)
    expect(pdfContrato.headers()['content-type']).toContain('application/pdf')

    const vistorias = await api.get(`${BASE}/api/v1/vistorias/`, { headers: { Authorization } })
    const vistoria = (await vistorias.json()).results[0]
    const laudo = await api.get(`${BASE}/api/v1/vistorias/${vistoria.id}/laudo/`, {
      headers: { Authorization },
    })
    expect(laudo.status()).toBe(200)
    expect(laudo.headers()['content-type']).toContain('application/pdf')

    await api.dispose()
  })

  test('27 · relatórios com dados reais do período', async () => {
    await irPara('Relatórios', 'Relatórios')
    await expect(pagina.getByText('Receita x despesa')).toBeVisible({ timeout: 15000 })
    await expect(pagina.getByText('Origem dos leads')).toBeVisible()
    await expect(pagina.getByText('Desempenho por corretor')).toBeVisible()
    await pagina.getByRole('button', { name: 'Atualizar' }).click()
    await pagina.waitForTimeout(800)
    await foto('50-relatorios')
  })

  test('28 · dashboard deixa de estar zerado', async () => {
    await irPara('Dashboard', 'Olá')
    const kpis = pagina.locator('[data-tour="kpis"]').first()
    await expect(kpis).toBeVisible()

    // O resultado do mês fica em zero de propósito: a receita é reconhecida na
    // competência da cobrança, e as pagas aqui são de meses à frente.
    await expect(kpis).toContainText('A receber')
    await expect(kpis).toContainText('R$ 3.100,00')
    await expect(kpis).toContainText('1 imóveis')
    await expect(kpis).toContainText('Leads abertos')
    await foto('51-dashboard-com-movimento')

    // A lista "precisa de você hoje" reflete a operação real.
    await expect(pagina.locator('[data-tour="precisa-hoje"]').first()).toBeVisible()
  })

  test('29 · notificações do período aparecem no sino', async () => {
    await pagina.getByRole('button', { name: 'Notificações' }).click()
    await expect(pagina.getByText(/notifica|Nada por aqui|lead|cobran/i).first()).toBeVisible()
    await foto('52-notificacoes')

    // Fecha com Esc, como qualquer menu suspenso.
    await pagina.keyboard.press('Escape')
    await expect(pagina.getByRole('button', { name: 'Notificações' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  test('30 · configurações: equipe, tabela de comissão e portais', async () => {
    await irPara('Configurações', 'Configurações')
    await foto('53-configuracoes-equipe')

    await pagina.getByRole('button', { name: 'Novo usuário' }).click()
    await pagina.getByLabel('Nome completo').fill('Bruno Corretor Novo')
    // E-mail é único: cada execução cria o seu.
    await pagina.getByLabel('E-mail').fill(`bruno.${Date.now()}@horizonteimoveis.com.br`)
    await pagina.getByLabel('Senha provisória').fill('horizonte-2026')
    await pagina.getByLabel('Papel').selectOption('CORRETOR')
    await pagina.getByRole('button', { name: 'Criar usuário' }).click()
    await confirmou('Usuário criado.')
    await foto('54-usuario-criado')

    // Percentual com vírgula precisa ser aceito: é como o brasileiro digita.
    await pagina.getByRole('button', { name: 'Tabela de comissão' }).click()
    await pagina.getByLabel('Comissão de venda (%)').fill('6,5')
    await pagina.getByRole('button', { name: 'Salvar' }).click()
    await confirmou('Tabela de comissão atualizada.')
    await foto('55-tabela-comissao')

    await pagina.getByRole('button', { name: 'Integrações' }).click()
    await expect(pagina.getByText('Portais')).toBeVisible()
    await expect(pagina.getByText('Fila de integração')).toBeVisible()
    await foto('56-integracoes')
  })

  test('31 · painel do guia mostra o progresso conquistado de verdade', async () => {
    await abrirGuia()
    const painel = pagina.getByRole('complementary', { name: 'Guia de uso' })
    await expect(painel).not.toContainText('0 de 12 missões concluídas')
    await expect(painel).toContainText(/Operando|Veterano|Imobiliária no controle/)
    await foto('57-guia-no-fim')
    await fecharGuia()
  })

  test('32 · corretor não enxerga o financeiro', async () => {
    await pagina.getByRole('button', { name: /Ana Ribeiro/ }).click()
    await pagina.getByRole('menuitem', { name: 'Sair' }).click()
    await expect(pagina).toHaveURL(/\/login/)

    await pagina.getByLabel('E-mail').fill('corretor@horizonteimoveis.com.br')
    await pagina.getByLabel('Senha').fill('horizonte-2026')
    const respostaLogin = pagina.waitForResponse((r) => r.url().includes('/auth/login/'))
    await pagina.getByRole('button', { name: 'Entrar' }).click()
    expect((await respostaLogin).status(), 'login do corretor recusado').toBe(200)
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá', {
      timeout: 15000,
    })
    await fecharTourSeAberto()

    await expect(pagina.getByRole('link', { name: 'Contas a receber' })).toHaveCount(0)
    // Rota bloqueada devolve ao dashboard em vez de mostrar tela que a API recusaria.
    await pagina.goto('/financeiro/receber')
    await expect(pagina).toHaveURL(/\/$/, { timeout: 15000 })
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá')
    await foto('58-corretor-sem-financeiro')
  })

  test('33 · rota inexistente mostra a tela de 404', async () => {
    await pagina.goto('/rota-que-nao-existe')
    await expect(pagina.getByText('404')).toBeVisible()
    await foto('59-nao-encontrado')
  })

  test('34 · nenhum erro de JavaScript em toda a varredura', async () => {
    expect(errosDeJs, `erros capturados:\n${errosDeJs.join('\n')}`).toEqual([])
  })
})
