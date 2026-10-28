import { expect, test } from '@playwright/test'

import { apagarImobiliaria } from './apoio'

// Dados únicos por execução: CNPJ, e-mail e subdomínio não podem repetir.
const marca = Date.now().toString().slice(-8)
const IMOBILIARIA = {
  razao: `Teste E2E ${marca} Imóveis Ltda`,
  fantasia: `Teste E2E ${marca}`,
  subdominio: `teste-e2e-${marca}`,
  cnpj: `${marca}000199`,
  email: `admin-${marca}@e2e.imobipro.test`,
  senha: 'casa-nova-2026!',
}

test.afterAll(() => apagarImobiliaria(IMOBILIARIA.subdominio))

test.describe('cadastre-se', () => {
  test('login leva ao cadastro, que cria a conta e abre o painel', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('link', { name: 'Cadastre-se' }).click()
    await expect(page).toHaveURL(/\/cadastro$/)

    await page.getByLabel('Razão social').fill(IMOBILIARIA.razao)
    await page.getByLabel('Nome fantasia').fill(IMOBILIARIA.fantasia)
    await expect(page.getByLabel('Endereço do site')).toHaveValue(IMOBILIARIA.subdominio)
    await page.getByLabel('CNPJ').fill(IMOBILIARIA.cnpj)
    await page.getByLabel('Nome completo').fill('Pessoa do Teste')
    await page.getByLabel('E-mail').fill(IMOBILIARIA.email)
    await page.locator('input[autocomplete="new-password"]').nth(0).fill(IMOBILIARIA.senha)
    await page.locator('input[autocomplete="new-password"]').nth(1).fill(IMOBILIARIA.senha)
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page).toHaveURL(/\/$/, { timeout: 15000 })
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Olá, Pessoa')
  })

  test('cadastro repetido mostra o erro no campo', async ({ page, request, baseURL }) => {
    // Garante a conta existente sem depender do teste anterior: se ele falhar,
    // o Playwright reinicia o worker e esta suíte roda isolada.
    await request.post(`${baseURL}/api/v1/auth/cadastro/`, {
      data: {
        razao_social: IMOBILIARIA.razao,
        cnpj: IMOBILIARIA.cnpj,
        subdominio: IMOBILIARIA.subdominio,
        nome_completo: 'Pessoa do Teste',
        email: IMOBILIARIA.email,
        senha: IMOBILIARIA.senha,
      },
    })

    await page.goto('/cadastro')
    await page.getByLabel('Razão social').fill(IMOBILIARIA.razao)
    await page.getByLabel('Nome fantasia').fill(IMOBILIARIA.fantasia)
    await page.getByLabel('CNPJ').fill(IMOBILIARIA.cnpj)
    await page.getByLabel('Nome completo').fill('Pessoa do Teste')
    await page.getByLabel('E-mail').fill(IMOBILIARIA.email)
    await page.locator('input[autocomplete="new-password"]').nth(0).fill(IMOBILIARIA.senha)
    await page.locator('input[autocomplete="new-password"]').nth(1).fill(IMOBILIARIA.senha)
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page.getByText('Já existe uma conta com este e-mail.')).toBeVisible()
    await expect(page.getByText('Já existe uma imobiliária com este CNPJ.')).toBeVisible()
    await expect(page).toHaveURL(/\/cadastro$/)
  })

  test('cadastro funciona em tela de celular', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/cadastro')
    const largura = await page.evaluate(() => document.documentElement.scrollWidth)
    expect(largura).toBeLessThanOrEqual(390)
    await expect(page.getByRole('button', { name: 'Criar conta' })).toBeVisible()
  })
})
