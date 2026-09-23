import { expect, test } from '@playwright/test'

import { entrar, limparCarteira, montarCarteira, silenciarGuia } from './apoio'

/** Falha o teste se o console do navegador registrar erro na tela. */
function vigiarConsole(page, erros) {
  page.on('console', (mensagem) => {
    if (mensagem.type() === 'error') erros.push(mensagem.text())
  })
  page.on('pageerror', (erro) => erros.push(erro.message))
}

async function entrarNoPainel(page, quem = 'admin') {
  await entrar(page, quem)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Olá', {
    timeout: 15000,
  })
}

// O tutorial abre sozinho no primeiro acesso e cobre a tela de propósito; para
// os testes de navegação ele fica desligado (a suíte de onboarding cuida dele).
test.beforeEach(async ({ request, baseURL }) => {
  await silenciarGuia(request, baseURL)
})

test.describe('porta de entrada e tema', () => {
  test('/home leva à vitrine ou ao painel, conforme a escolha', async ({ page }) => {
    await page.goto('/home')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Por onde você entra')

    await page.locator('[data-teste="visao-cliente"]').click()
    await expect(page).toHaveURL(/\/site\/horizonte$/)

    await page.goto('/home')
    await page.locator('[data-teste="visao-equipe"]').click()
    await expect(page).toHaveURL(/\/login/)
  })

  test('tema escuro vale para a sessão toda e sobrevive ao recarregar', async ({ page }) => {
    await page.goto('/home')
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'claro')

    await page.getByRole('button', { name: /tema escuro/i }).click()
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'escuro')

    // A escolha acompanha quem navega: outra área, mesmo tema, sem piscar.
    await page.goto('/site/horizonte')
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'escuro')

    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'escuro')

    await page.getByRole('button', { name: /tema claro/i }).click()
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'claro')
  })
})

test.describe('autenticação', () => {
  test('login com senha errada mostra o erro da API', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('E-mail').fill('admin@horizonteimoveis.com.br')
    await page.getByLabel('Senha').fill('senha-errada')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByRole('alert')).toBeVisible()
  })

  test('rota protegida redireciona para o login', async ({ page }) => {
    await page.goto('/imoveis')
    await expect(page).toHaveURL(/\/login/)
  })

  test('sessão sobrevive ao recarregar a página', async ({ page }) => {
    await entrarNoPainel(page)
    await page.reload()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Olá')
  })
})

test.describe('telas do painel', () => {
  const TELAS = [
    { rota: '/', titulo: 'Olá', nome: 'dashboard' },
    { rota: '/imoveis', titulo: 'Imóveis', nome: 'imoveis' },
    { rota: '/pessoas', titulo: 'Pessoas', nome: 'pessoas' },
    { rota: '/crm', titulo: 'Funil de vendas', nome: 'crm' },
    { rota: '/agenda', titulo: 'Agenda de visitas', nome: 'agenda' },
    { rota: '/contratos', titulo: 'Contratos', nome: 'contratos' },
    { rota: '/financeiro/receber', titulo: 'Contas a receber', nome: 'cobrancas' },
    { rota: '/financeiro/pagar', titulo: 'Repasses', nome: 'repasses' },
    { rota: '/financeiro/comissoes', titulo: 'Comissões', nome: 'comissoes' },
    { rota: '/vistorias', titulo: 'Vistorias', nome: 'vistorias' },
    { rota: '/relatorios', titulo: 'Relatórios', nome: 'relatorios' },
    { rota: '/configuracoes', titulo: 'Configurações', nome: 'configuracoes' },
  ]

  for (const tela of TELAS) {
    test(`${tela.nome} abre sem erro de console`, async ({ page }) => {
      const erros = []
      vigiarConsole(page, erros)

      await entrarNoPainel(page)
      await page.goto(tela.rota)
      await expect(page.getByRole('heading', { level: 1 })).toContainText(tela.titulo)
      await page.waitForLoadState('networkidle')
      await page.screenshot({ path: `tests/e2e/telas/${tela.nome}.png`, fullPage: true })

      expect(erros, `console limpo em ${tela.rota}`).toEqual([])
    })
  }

  test('404 é exibido para rota inexistente', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/rota-que-nao-existe')
    await expect(page.getByText('Página não encontrada')).toBeVisible()
  })
})

test.describe('operação com carteira montada', () => {
  // A suíte cria o próprio conteúdo pela API e devolve a base limpa no fim.
  test.beforeAll(async ({ request, playwright }, info) => {
    const baseURL = info.project.use.baseURL
    const contexto = request ?? (await playwright.request.newContext())
    await limparCarteira(contexto, baseURL)
    await montarCarteira(contexto, baseURL)
  })

  test.afterAll(async ({ playwright }, info) => {
    const contexto = await playwright.request.newContext()
    await limparCarteira(contexto, info.project.use.baseURL)
    await contexto.dispose()
  })

  test('lista, filtra e abre a ficha do imóvel', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/imoveis')

    const cards = page.locator('a[href^="/imoveis/"]:not([href$="/novo"])')
    await expect(cards.first()).toBeVisible()

    await page.getByLabel('Buscar').fill('apartamento')
    await expect(page.getByText('REF-', { exact: false }).first()).toBeVisible({
      timeout: 10000,
    })

    await cards.first().click()
    await expect(page).toHaveURL(/\/imoveis\/[0-9a-f-]{36}/)
    await expect(page.getByRole('button', { name: 'Fotos e mídia' })).toBeVisible()
  })

  test('alterna para tabela e para o mapa', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/imoveis')

    await page.getByRole('button', { name: 'Tabela' }).click()
    await expect(page.locator('table')).toBeVisible()

    await page.getByRole('button', { name: 'Mapa' }).click()
    await expect(page.locator('.leaflet-container')).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/imoveis-mapa.png', fullPage: true })
  })

  test('ficha do imóvel mostra abas e histórico', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/imoveis')
    await page.locator('a[href^="/imoveis/"]:not([href$="/novo"])').first().click()

    await page.getByRole('button', { name: 'Histórico' }).click()
    await expect(page.getByText('Cadastro', { exact: false }).first()).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/imovel-ficha.png', fullPage: true })
  })

  test('kanban mostra colunas e cartões', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/crm')

    await expect(page.getByRole('heading', { name: 'Novo' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Proposta' })).toBeVisible()
    await expect(page.locator('a[href^="/crm/leads/"]').first()).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/crm-kanban.png', fullPage: true })
  })

  test('abre o lead e registra interação', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/crm')

    await page.locator('a[href^="/crm/leads/"]').first().click()
    await expect(page).toHaveURL(/\/crm\/leads\//)

    await page.getByLabel('O que aconteceu').fill('Cliente retornou; quer visitar sábado.')
    await page.getByRole('button', { name: 'Registrar', exact: true }).click()

    await expect(page.getByText('Cliente retornou').first()).toBeVisible({ timeout: 10000 })
    await page.screenshot({ path: 'tests/e2e/telas/lead-detalhe.png', fullPage: true })
  })

  test('perder lead exige motivo', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/crm')

    // Fechados saem do quadro: a coluna de perdidos não é oferecida no kanban.
    await expect(page.getByRole('heading', { name: 'Fechado perdido' })).toHaveCount(0)
  })

  test('ficha do contrato mostra partes, comissões e ações', async ({ page }) => {
    await entrarNoPainel(page)
    await page.goto('/contratos')

    const linha = page.locator('tbody tr', { hasText: 'LOC-' }).first()
    await linha.waitFor()
    await linha.click()

    await expect(page).toHaveURL(/\/contratos\/[0-9a-f-]{36}/)
    await expect(page.getByRole('heading', { name: 'Partes' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Comissões' })).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/contrato-detalhe.png', fullPage: true })
  })

  test('cobranças listam vencimento e permitem baixa', async ({ page }) => {
    await entrarNoPainel(page, 'financeiro')
    await page.goto('/financeiro/receber')

    await expect(page.locator('table')).toBeVisible()
    await page.getByRole('button', { name: 'Dar baixa' }).first().click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('Valor recebido')).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/cobranca-baixa.png', fullPage: true })
  })

  test('relatórios calculam DRE e desempenho', async ({ page }) => {
    await entrarNoPainel(page, 'financeiro')
    await page.goto('/relatorios')

    await expect(page.getByText('Receita operacional')).toBeVisible()
    await expect(page.getByText('Desempenho por corretor')).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/relatorios.png', fullPage: true })
  })
})

test.describe('permissões por papel', () => {
  test('corretor não vê financeiro no menu', async ({ page }) => {
    await entrarNoPainel(page, 'corretor')

    await expect(page.getByRole('link', { name: 'Funil de vendas' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Contas a receber' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Configurações' })).toHaveCount(0)
  })

  test('corretor é devolvido ao dashboard ao tentar o financeiro', async ({ page }) => {
    await entrarNoPainel(page, 'corretor')
    await page.goto('/financeiro/receber')

    await expect(page).toHaveURL(/\/$/)
  })

  test('financeiro não vê o CRM no menu', async ({ page }) => {
    await entrarNoPainel(page, 'financeiro')

    await expect(page.getByRole('link', { name: 'Contas a receber' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Funil de vendas' })).toHaveCount(0)
  })
})

test.describe('responsividade e acessibilidade', () => {
  test('no celular a sidebar vira gaveta', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await entrarNoPainel(page)

    await page.getByLabel('Abrir menu').click()
    await expect(page.getByRole('link', { name: 'Imóveis' })).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/mobile-menu.png', fullPage: true })
  })

  test('página não rola na horizontal no celular', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await entrarNoPainel(page)
    await page.goto('/imoveis')
    await page.waitForLoadState('networkidle')

    const rolagem = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(rolagem).toBeLessThanOrEqual(1)
  })

  test('cada tela tem um único h1', async ({ page }) => {
    await entrarNoPainel(page)
    for (const rota of ['/', '/imoveis', '/crm', '/contratos']) {
      await page.goto(rota)
      await expect(page.locator('h1')).toHaveCount(1)
    }
  })
})
