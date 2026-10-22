import { expect, test } from '@playwright/test'

import { zerarOperacao } from './apoio.js'

const ADMIN = { email: 'admin@horizonteimoveis.com.br', senha: 'horizonte-2026' }

/**
 * O progresso do guia é persistido por usuário: sem zerar antes de cada teste,
 * um tour concluído em um caso vazaria para o seguinte.
 */
async function autenticar(request, baseURL) {
  const login = await request.post(`${baseURL}/api/v1/auth/login/`, {
    data: { email: ADMIN.email, password: ADMIN.senha },
  })
  const { access } = await login.json()
  return { Authorization: `Bearer ${access}` }
}

async function reiniciarGuia(request, baseURL) {
  const headers = await autenticar(request, baseURL)
  await request.post(`${baseURL}/api/v1/onboarding/reiniciar/`, { headers })
}

/** Remove o cadastro de teste para o caso poder rodar quantas vezes precisar. */
async function limparPessoasDeTeste(request, baseURL) {
  const headers = await autenticar(request, baseURL)
  const lista = await request.get(`${baseURL}/api/v1/pessoas/?search=Tutorial`, { headers })
  for (const pessoa of (await lista.json()).results ?? []) {
    await request.delete(`${baseURL}/api/v1/pessoas/${pessoa.id}/`, { headers })
  }
}

async function entrar(page) {
  await page.goto('/login')
  await page.getByLabel('E-mail').fill(ADMIN.email)
  await page.getByLabel('Senha').fill(ADMIN.senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Olá', {
    timeout: 15000,
  })
}

/**
 * Fecha o tour de boas-vindas, que abre sozinho no primeiro acesso.
 *
 * Ele aparece só depois de o progresso chegar da API; sem esperar, o clique
 * seguinte cairia no overlay do tour em vez do botão pretendido.
 */
async function fecharTourInicial(page) {
  const sair = page.getByRole('button', { name: 'Sair do tutorial' })
  await sair.waitFor({ state: 'visible', timeout: 15000 })
  await sair.click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

test.describe('onboarding gamificado', () => {
  // A base precisa estar realmente vazia: as missões são verificadas contra os
  // dados reais, e sobras de outra suíte contariam como progresso.
  test.beforeAll(() => zerarOperacao())

  test.beforeEach(async ({ request, baseURL }) => {
    await reiniciarGuia(request, baseURL)
    await limparPessoasDeTeste(request, baseURL)
  })

  test('tutorial de boas-vindas abre sozinho no primeiro acesso', async ({ page }) => {
    await entrar(page)

    const balao = page.getByRole('dialog')
    await expect(balao).toBeVisible()
    await expect(balao).toContainText('Passo 1 de 5')
    await expect(balao).toContainText('O menu segue o fluxo do negócio')
    await page.screenshot({ path: 'tests/e2e/telas/tour-passo-1.png' })
  })

  test('avança pelos passos e conclui o roteiro', async ({ page }) => {
    await entrar(page)

    await expect(page.getByRole('dialog')).toContainText('Passo 1 de 5')
    await page.getByRole('button', { name: 'Próximo' }).click()
    await expect(page.getByRole('dialog')).toContainText('Passo 2 de 5')

    await page.getByRole('button', { name: 'Voltar' }).click()
    await expect(page.getByRole('dialog')).toContainText('Passo 1 de 5')

    for (let passo = 0; passo < 4; passo += 1) {
      await page.getByRole('button', { name: 'Próximo' }).click()
    }
    await expect(page.getByRole('dialog')).toContainText('Passo 5 de 5')
    await page.getByRole('button', { name: 'Concluir' }).click()

    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  test('painel de missões mostra progresso, trilhas e dica da próxima', async ({ page }) => {
    await entrar(page)
    await fecharTourInicial(page)

    await page.getByRole('button', { name: /Tutorial/ }).click()

    const painel = page.getByRole('complementary', { name: 'Guia de uso' })
    await expect(painel).toBeVisible()
    await expect(painel).toContainText('Começando')
    await expect(painel).toContainText('missões concluídas')
    await expect(painel).toContainText('Montar a carteira')
    await expect(painel).toContainText('Como fazer')
    await page.screenshot({ path: 'tests/e2e/telas/painel-missoes.png' })
  })

  test('botão do tutorial mostra quantas missões faltam', async ({ page }) => {
    await entrar(page)
    await fecharTourInicial(page)

    // Base sem dados reais: todas as missões seguem pendentes.
    await expect(page.getByRole('button', { name: /Tutorial/ })).toContainText('12')
  })

  test('missão leva para a tela certa', async ({ page }) => {
    await entrar(page)
    await fecharTourInicial(page)

    await page.getByRole('button', { name: /Tutorial/ }).click()
    await page.getByRole('button', { name: 'Ir para a tela →' }).first().click()

    await expect(page).toHaveURL(/\/pessoas/)
  })

  test('tour guiado troca de tela sozinho e destaca o alvo', async ({ page }) => {
    await entrar(page)
    await fecharTourInicial(page)

    await page.getByRole('button', { name: /Tutorial/ }).click()
    await page
      .getByRole('listitem')
      .filter({ hasText: 'Captar um imóvel' })
      .getByRole('button')
      .click()

    // O primeiro passo desse roteiro mora em /pessoas.
    await expect(page).toHaveURL(/\/pessoas/)
    await expect(page.getByRole('dialog')).toContainText('Primeiro o dono, depois o imóvel')
    await expect(page.getByRole('dialog')).toContainText('Clique no botão destacado')
    await page.screenshot({ path: 'tests/e2e/telas/tour-coach-mark.png' })
  })

  test('cumprir a missão de verdade avança o progresso e comemora', async ({
    page,
    request,
    baseURL,
  }) => {
    await entrar(page)
    await fecharTourInicial(page)

    // Navega pelo menu (como o usuário faz) em vez de recarregar a página.
    await page.getByRole('link', { name: 'Pessoas' }).click()
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Pessoas')
    await page.getByRole('button', { name: 'Nova pessoa' }).first().click()
    await page.getByLabel('Nome / Razão social').fill('Proprietário do Tutorial')
    await page.getByLabel('CPF/CNPJ').fill('529.982.247-25')
    await page.getByRole('button', { name: 'Salvar' }).click()

    await expect(page.getByText('Cadastro salvo.')).toBeVisible({ timeout: 10000 })

    // O contador do guia cai de 12 para 11 sem recarregar a página.
    await expect(page.getByRole('button', { name: /Tutorial/ })).toContainText('11', {
      timeout: 15000,
    })
    await expect(page.getByRole('status').filter({ hasText: 'Missão cumprida!' })).toBeVisible()
    await page.screenshot({ path: 'tests/e2e/telas/missao-cumprida.png' })

    await page.getByRole('button', { name: /Tutorial/ }).click()
    const painel = page.getByRole('complementary', { name: 'Guia de uso' })
    // 10 pontos ainda é o primeiro nível; "Aprendiz" começa em 25.
    await expect(painel).toContainText('10 / 205 pontos')
    await expect(painel).toContainText('1 de 12 missões concluídas')

    await limparPessoasDeTeste(request, baseURL)
  })

  test('sair do tutorial não o marca como concluído', async ({ page }) => {
    await entrar(page)
    await page.getByRole('button', { name: 'Sair do tutorial' }).click()

    await page.reload()

    // Como não foi concluído, o guia volta a sugerir no próximo acesso.
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
  })
})
