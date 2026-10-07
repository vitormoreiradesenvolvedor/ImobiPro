/**
 * Jornada do cliente, do anúncio ao portal do inquilino.
 *
 * Percorre a vitrine pública, o pedido de visita sem cadastro, o atendimento do
 * lado da imobiliária, a candidatura com envio de documentos por link e, no
 * fim, o acesso do inquilino ao próprio contrato.
 *
 * Encadeada de propósito: o imóvel que aparece na vitrine é o mesmo que vira
 * contrato e aparece no portal.
 */

import { expect, request as apiRequest, test } from '@playwright/test'

import { autenticar, zerarOperacao } from './apoio.js'

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080'
const TELAS = 'tests/e2e/telas/cliente'
const ADMIN = { email: 'admin@horizonteimoveis.com.br', senha: 'horizonte-2026' }

const CLIENTE = {
  nome: 'Marina Pretendente',
  telefone: '35991234567',
  email: 'marina.pretendente@teste.local',
  cpf: '529.982.247-25',
}

test.describe.configure({ mode: 'serial' })

let pagina
let cabecalhos
let api
let codigoDoImovel
let protocolo
let linkDaCandidatura
let acessoDoInquilino

async function foto(nome) {
  await pagina.screenshot({ path: `${TELAS}/${nome}.png`, fullPage: true })
}

/** Falha cedo e com a mensagem da API; erro escondido aqui vira mistério lá na frente. */
async function conferir(resposta, oque) {
  if (resposta.status() >= 300) {
    throw new Error(`${oque} falhou (${resposta.status()}): ${await resposta.text()}`)
  }
  return resposta.json()
}

/** Monta um imóvel publicado pela API: o alvo do teste é a jornada, não o cadastro. */
async function publicarImovel() {
  const pessoa = await api.post(`${BASE}/api/v1/pessoas/`, {
    headers: cabecalhos,
    data: {
      tipo: 'FISICA',
      nome: 'Helena Proprietária',
      cpf_cnpj: '168.995.350-09',
      telefone: '35998887766',
    },
  })
  const proprietario = await conferir(pessoa, 'cadastro do proprietário')

  const criado = await api.post(`${BASE}/api/v1/imoveis/`, {
    headers: cabecalhos,
    data: {
      titulo: 'Apartamento 302 com varanda',
      descricao: 'Dois quartos, varanda e vaga coberta.',
      tipo: 'APARTAMENTO',
      finalidade: 'LOCACAO',
      proprietario: proprietario.id,
      valor_locacao: '2500.00',
      quartos: 2,
      banheiros: 2,
      area_util: '68',
      // Publicar locação exige matrícula: é regra do sistema, não do teste.
      matricula: 'MAT-45231',
      endereco: {
        cep: '37200066',
        logradouro: 'Rua Central',
        numero: '302',
        bairro: 'Centro',
        cidade: 'Lavras',
        uf: 'MG',
        latitude: '-21.245',
        longitude: '-44.997',
      },
    },
  })
  const imovel = await conferir(criado, 'cadastro do imóvel')

  const png = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64',
  )
  for (let indice = 0; indice < 5; indice += 1) {
    const envio = await api.post(`${BASE}/api/v1/imoveis/${imovel.id}/fotos/`, {
      headers: cabecalhos,
      multipart: {
        arquivo: { name: `foto-${indice}.png`, mimeType: 'image/png', buffer: png },
      },
    })
    await conferir(envio, `envio da foto ${indice}`)
  }

  const publicacao = await api.post(`${BASE}/api/v1/imoveis/${imovel.id}/publicar/`, {
    headers: cabecalhos,
  })
  await conferir(publicacao, 'publicação do imóvel')

  return imovel
}

test.beforeAll(async ({ browser }) => {
  zerarOperacao()
  api = await apiRequest.newContext()
  cabecalhos = await autenticar(api, BASE)
  const imovel = await publicarImovel()
  codigoDoImovel = imovel.codigo

  pagina = await browser.newPage()
})

test.afterAll(async () => {
  await pagina?.close()
  await api?.dispose()
})

test.describe('jornada do cliente', () => {
  test('01 · vitrine mostra o catálogo por categoria', async () => {
    await pagina.goto('/site/horizonte')

    await expect(pagina.getByRole('heading', { level: 1 })).toContainText(
      'O próximo endereço da sua vida',
    )
    // A vitrine sai com a marca da imobiliária, não com a cor padrão do produto.
    await expect(
      pagina.getByRole('banner').getByText('Horizonte Imóveis').first(),
    ).toBeVisible()
    await expect(pagina.getByText('Encontre pelo que importa')).toBeVisible()
    await expect(pagina.getByRole('button', { name: /Apartamento/ }).first()).toBeVisible()
    await expect(pagina.getByText('Apartamento 302 com varanda').first()).toBeVisible()
    await foto('01-vitrine')
  })

  test('02 · filtro de categoria muda a lista e vive na URL', async () => {
    await pagina.getByRole('button', { name: /^Centro/ }).click()
    await pagina.waitForTimeout(1200)

    await expect(pagina).toHaveURL(/bairro=Centro/)
    await expect(pagina.getByText('Apartamento 302 com varanda').first()).toBeVisible()
    await foto('02-filtro-por-bairro')
  })

  test('03 · ficha pública tem galeria e mapa de verdade', async () => {
    await pagina.goto(`/site/horizonte/imovel/${codigoDoImovel}`)

    await expect(pagina.getByRole('heading', { level: 1 })).toContainText(
      'Apartamento 302 com varanda',
    )
    await expect(pagina.getByText('Onde fica')).toBeVisible()
    // O mapa é o Leaflet renderizando tiles do OpenStreetMap.
    await expect(pagina.locator('.leaflet-container')).toBeVisible()
    await expect(pagina.locator('.leaflet-marker-icon')).toBeVisible()
    await foto('03-ficha-publica')
  })

  test('04 · visitante pede visita sem criar conta', async () => {
    await pagina.getByLabel('Seu nome').fill(CLIENTE.nome)
    await pagina.getByLabel('Telefone').fill(CLIENTE.telefone)
    await pagina.getByLabel('E-mail').fill(CLIENTE.email)
    await pagina.getByLabel('Mensagem').fill('Posso visitar no sábado de manhã?')
    await pagina.getByRole('button', { name: 'Pedir visita' }).click()

    await expect(pagina.getByText('Pedido registrado')).toBeVisible({ timeout: 15000 })
    const texto = await pagina
      .getByText(/ATD-\d{4}-\d{6}/)
      .first()
      .innerText()
    protocolo = /ATD-\d{4}-\d{6}/.exec(texto)[0]
    await foto('04-pedido-enviado')
  })

  test('05 · acompanhamento exige protocolo e contato', async () => {
    await pagina.goto('/site/horizonte/acompanhar')

    await pagina.getByLabel('Protocolo').fill(protocolo)
    await pagina.getByLabel('Telefone ou e-mail').fill('11999990000')
    await pagina.getByRole('button', { name: 'Consultar' }).click()
    await expect(pagina.getByRole('alert')).toBeVisible()

    await pagina.getByLabel('Telefone ou e-mail').fill(CLIENTE.telefone)
    await pagina.getByRole('button', { name: 'Consultar' }).click()

    await expect(pagina.getByText(protocolo)).toBeVisible({ timeout: 15000 })
    await expect(pagina.getByText('Pedido recebido pelo site')).toBeVisible()
    await foto('05-acompanhamento')
  })

  test('06 · pedido chega na fila da imobiliária com prazo', async () => {
    await pagina.goto('/login')
    await pagina.getByLabel('E-mail').fill(ADMIN.email)
    await pagina.getByLabel('Senha').fill(ADMIN.senha)
    await pagina.getByRole('button', { name: 'Entrar' }).click()
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá', {
      timeout: 15000,
    })
    const sair = pagina.getByRole('button', { name: 'Sair do tutorial' })
    if (await sair.isVisible().catch(() => false)) await sair.click()

    await pagina.goto('/atendimento')
    await expect(pagina.getByText(protocolo)).toBeVisible({ timeout: 15000 })
    await pagina.getByRole('row', { name: new RegExp(protocolo) }).click()
    await expect(pagina.getByText('Posso visitar no sábado')).toBeVisible()
    await foto('06-fila-de-atendimento')
  })

  test('07 · responder e agendar cria a visita na agenda', async () => {
    await pagina.getByLabel('Responder').fill('Podemos sábado às 10h?')
    await pagina.getByRole('button', { name: 'Registrar' }).click()
    await expect(pagina.getByText('Resposta enviada ao interessado.')).toBeVisible({
      timeout: 15000,
    })

    const daquiADias = new Date(Date.now() + 2 * 24 * 3600 * 1000)
    const quando = `${daquiADias.toISOString().slice(0, 10)}T10:00`
    await pagina.getByLabel('Agendar visita').fill(quando)
    await pagina.getByRole('button', { name: 'Confirmar visita' }).click()
    await expect(pagina.getByText('Atendimento atualizado.')).toBeVisible({
      timeout: 15000,
    })

    await pagina.goto('/agenda')
    await pagina.getByLabel('Dia').fill(daquiADias.toISOString().slice(0, 10))
    await expect(pagina.getByText(CLIENTE.nome).first()).toBeVisible({ timeout: 15000 })
    await foto('07-visita-na-agenda')
  })

  test('08 · candidatura nasce com link para o pretendente', async () => {
    await pagina.goto('/candidaturas')
    await pagina.getByRole('button', { name: 'Nova candidatura' }).first().click()

    await pagina.getByLabel('Imóvel').selectOption({ index: 1 })
    await pagina.getByLabel('Nome').fill(CLIENTE.nome)
    await pagina.getByLabel('CPF').fill(CLIENTE.cpf)
    await pagina.getByLabel('Telefone').fill(CLIENTE.telefone)
    await pagina.getByLabel('E-mail').fill(CLIENTE.email)
    await pagina.getByLabel('Renda mensal').fill('9000,00')
    await pagina.getByRole('button', { name: 'Abrir candidatura' }).click()

    await expect(pagina.getByText(/CAD-\d{4}-\d{6}/).first()).toBeVisible({
      timeout: 15000,
    })
    const texto = await pagina
      .getByText(/\/candidatura\/horizonte\//)
      .first()
      .innerText()
    linkDaCandidatura = texto.trim()
    await foto('08-candidatura-aberta')
  })

  test('09 · pretendente envia os documentos pelo link, sem conta', async () => {
    const caminho = new URL(linkDaCandidatura).pathname
    await pagina.goto(caminho)

    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Sua candidatura')
    await expect(pagina.getByText('Documento de identidade')).toBeVisible()

    const arquivo = {
      name: 'documento.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('documento de teste'),
    }
    for (let indice = 0; indice < 4; indice += 1) {
      await pagina.locator('input[type="file"]').first().setInputFiles(arquivo)
      await pagina.waitForTimeout(1200)
    }

    await expect(pagina.getByText('Tudo recebido')).toBeVisible({ timeout: 15000 })
    await expect(pagina.getByText('Em análise').first()).toBeVisible()
    await foto('09-documentos-enviados')
  })

  test('10 · análise confere documento por documento antes de aprovar', async () => {
    await pagina.goto('/candidaturas')
    await pagina.getByRole('row', { name: /CAD-/ }).click()
    await expect(pagina.getByText('Link do pretendente')).toBeVisible({ timeout: 15000 })

    // Aprovar antes da conferência não pode passar.
    await expect(pagina.getByRole('button', { name: 'Aprovar' })).toBeDisabled()

    // Conferência é item a item: o botão some conforme cada documento é aceito.
    const conferir = pagina.getByRole('button', { name: 'Conferir' })
    for (let indice = 4; indice > 0; indice -= 1) {
      await expect(conferir).toHaveCount(indice)
      await conferir.first().click()
      await expect(conferir).toHaveCount(indice - 1, { timeout: 15000 })
    }

    await pagina.getByRole('button', { name: 'Aprovar' }).click()
    await expect(pagina.getByText('Candidatura atualizada.')).toBeVisible({
      timeout: 15000,
    })
    await foto('10-candidatura-aprovada')
  })

  test('11 · aprovação vira contrato com locador e locatário', async () => {
    await pagina.getByRole('button', { name: 'Gerar contrato' }).click()
    await pagina.getByRole('button', { name: 'Criar rascunho' }).click()

    await expect(pagina.getByText(/Contrato LOC-\d{4}-\d{4} criado/).first()).toBeVisible({
      timeout: 15000,
    })
    await foto('11-contrato-gerado')
  })

  test('12 · contrato ativado libera o acesso do inquilino', async () => {
    await pagina.goto('/contratos')
    await pagina.getByRole('row', { name: /LOC-/ }).first().click()

    await pagina.getByRole('button', { name: 'Ativar contrato' }).click()
    await expect(pagina.getByText(/Ativo/).first()).toBeVisible({ timeout: 15000 })

    await pagina.getByRole('button', { name: 'Acesso do inquilino' }).click()
    await expect(pagina.getByText('Senha provisória')).toBeVisible({ timeout: 15000 })

    const bloco = await pagina.getByRole('dialog').innerText()
    acessoDoInquilino = {
      email: /([\w.+-]+@[\w.-]+)/.exec(bloco)[1],
      senha: /Senha provisória:\s*(\S+)/.exec(bloco)[1],
    }
    await foto('12-acesso-criado')

    await pagina.keyboard.press('Escape')
    await expect(pagina.getByText('Senha provisória')).toHaveCount(0, { timeout: 15000 })
  })

  test('13 · inquilino entra e vê só o contrato dele', async () => {
    await pagina.getByRole('button', { name: /Ana Ribeiro/ }).click()
    await pagina.getByRole('menuitem', { name: 'Sair' }).click()
    await expect(pagina).toHaveURL(/\/login/)

    await pagina.getByLabel('E-mail').fill(acessoDoInquilino.email)
    await pagina.getByLabel('Senha').fill(acessoDoInquilino.senha)
    await pagina.getByRole('button', { name: 'Entrar' }).click()

    // Cliente não cai no painel: vai direto para o portal.
    await expect(pagina).toHaveURL(/\/portal/, { timeout: 15000 })
    await expect(pagina.getByRole('heading', { level: 1 })).toContainText('Olá')
    await expect(pagina.getByText(/LOC-\d{4}-\d{4}/)).toBeVisible()
    await foto('13-portal-do-inquilino')
  })

  test('14 · inquilino vê boletos e abre chamado de manutenção', async () => {
    await pagina.getByRole('button', { name: 'Boletos' }).click()
    await expect(pagina.getByText('Histórico')).toBeVisible()

    await pagina.getByRole('button', { name: 'Chamados' }).click()
    await pagina
      .getByLabel('O que está acontecendo no imóvel?')
      .fill('Infiltração no teto do banheiro.')
    await pagina.getByRole('button', { name: 'Abrir chamado' }).click()

    await expect(pagina.getByText('Chamado aberto')).toBeVisible({ timeout: 15000 })
    await expect(pagina.getByText('Infiltração no teto do banheiro.')).toBeVisible()
    await foto('14-chamado-aberto')
  })

  test('15 · painel da imobiliária continua fora do alcance do cliente', async () => {
    for (const rota of ['/imoveis', '/contratos', '/financeiro/receber']) {
      await pagina.goto(rota)
      await expect(pagina).toHaveURL(/\/portal/, { timeout: 15000 })
    }
  })
})
