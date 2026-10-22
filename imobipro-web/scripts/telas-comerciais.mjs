/**
 * Capturas para o material comercial (slides, propostas, site).
 *
 *   node scripts/telas-comerciais.mjs
 *
 * Usa a base de demonstração carregada, sem o "palco" do vídeo: são as telas
 * exatamente como o cliente vê, em alta resolução.
 */

import { mkdir, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from '@playwright/test'

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SAIDA = path.join(RAIZ, 'midia', 'telas-comerciais')
const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080'

const esperar = (ms) => new Promise((r) => setTimeout(r, ms))

const CENAS = [
  { arquivo: 'painel', rota: '/', espera: 2200 },
  { arquivo: 'carteira', rota: '/imoveis', espera: 2400 },
  {
    arquivo: 'mapa',
    rota: '/imoveis',
    espera: 3200,
    antes: async (pagina) => pagina.getByRole('button', { name: 'Mapa' }).click(),
  },
  { arquivo: 'funil', rota: '/crm', espera: 2400 },
  { arquivo: 'agenda', rota: '/agenda', espera: 2000 },
  { arquivo: 'contratos', rota: '/contratos', espera: 2000 },
  { arquivo: 'cobrancas', rota: '/financeiro/receber', espera: 2200 },
  { arquivo: 'repasses', rota: '/financeiro/pagar', espera: 2200 },
  { arquivo: 'comissoes', rota: '/financeiro/comissoes', espera: 2000 },
  { arquivo: 'vistorias', rota: '/vistorias', espera: 2000 },
  { arquivo: 'relatorios', rota: '/relatorios', espera: 2600 },
  { arquivo: 'configuracoes', rota: '/configuracoes', espera: 2200 },
  // O site é público: a mesma sessão serve, e a sessão não aparece na tela.
  { arquivo: 'site-vitrine', rota: '/site/horizonte', espera: 2600 },
  { arquivo: 'site-ficha', rota: '/site/horizonte/imovel/REF-000002', espera: 3400 },
]

async function principal() {
  await rm(SAIDA, { recursive: true, force: true })
  await mkdir(SAIDA, { recursive: true })

  const navegador = await chromium.launch()
  const contexto = await navegador.newContext({
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 1.5,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    baseURL: BASE,
  })
  const pagina = await contexto.newPage()

  await pagina.goto('/login')
  await pagina.getByLabel('E-mail').fill('admin@horizonteimoveis.com.br')
  await pagina.getByLabel('Senha').fill('horizonte-2026')
  await pagina.getByRole('button', { name: 'Entrar' }).click()
  await esperar(3000)

  const sair = pagina.getByRole('button', { name: 'Sair do tutorial' })
  if (await sair.isVisible().catch(() => false)) await sair.click()
  await esperar(800)

  for (const cena of CENAS) {
    await pagina.goto(cena.rota)
    await esperar(1200)
    if (cena.antes) await cena.antes(pagina)
    await esperar(cena.espera)
    await pagina.screenshot({ path: path.join(SAIDA, `${cena.arquivo}.png`) })
    console.log(cena.arquivo)
  }

  // O guia aberto: é o argumento de adoção da equipe.
  await pagina.goto('/')
  await esperar(1500)
  await pagina.getByRole('button', { name: /Tutorial/ }).click()
  await esperar(1500)
  await pagina.screenshot({ path: path.join(SAIDA, 'guia.png') })
  console.log('guia')

  // O portal do inquilino é outra sessão, e a senha nasce na liberação do
  // acesso. Sem ela em SENHA_INQUILINO, a cena é pulada em vez de quebrar.
  const senhaInquilino = process.env.SENHA_INQUILINO
  if (senhaInquilino) {
    await contexto.clearCookies()
    await pagina.goto('/login')
    await pagina.evaluate(() => localStorage.clear())
    await pagina.goto('/login')
    await pagina.getByLabel('E-mail').fill(process.env.EMAIL_INQUILINO || 'paulo@cliente.test')
    await pagina.getByLabel('Senha').fill(senhaInquilino)
    await pagina.getByRole('button', { name: 'Entrar' }).click()
    await esperar(3000)
    await pagina.screenshot({ path: path.join(SAIDA, 'portal-inquilino.png') })
    console.log('portal-inquilino')
  } else {
    console.log('portal-inquilino pulado: defina SENHA_INQUILINO')
  }

  await contexto.close()
  await navegador.close()
}

principal().catch((erro) => {
  console.error(erro)
  process.exit(1)
})
