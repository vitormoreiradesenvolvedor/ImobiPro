/**
 * Grava o vídeo de apresentação do ImobiPro navegando no sistema de verdade.
 *
 *   node scripts/gravar-demo.mjs
 *
 * Nada aqui é montagem: o que aparece na tela é a aplicação rodando contra a
 * API. O "palco" (cartelas, legendas, cursor e halo) é injetado na página só
 * para narrar o que está acontecendo some junto com o navegador.
 *
 * Saída: vídeo .webm em `midia/bruto/` e a marcação de tempo das falas em
 * `midia/narracao.json`, usada para gerar legenda e roteiro de locução.
 */

import { mkdir, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from '@playwright/test'

import { encerrarVoz, motorDeVoz, sintetizar, vozDisponivel } from './voz.mjs'

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SAIDA = path.join(RAIZ, 'midia')
const BRUTO = path.join(SAIDA, 'bruto')
const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080'
const CONTA = { email: 'admin@horizonteimoveis.com.br', senha: 'horizonte-2026' }
const SITE = '/site/horizonte'

const falas = []
let inicio = 0

/** Pausa curta depois de cada fala, para a locução não emendar na seguinte. */
const RESPIRO = 0.45
const comVoz = vozDisponivel()

/**
 * Ensaio: percorre o roteiro só para sintetizar as falas, sem gravar vídeo.
 *
 * Sintetizar durante a gravação deixa a tela parada enquanto o modelo carrega,
 * e o vídeo ganha buracos de vinte segundos. Com o ensaio antes, a gravação
 * encontra tudo pronto em cache e corre no ritmo da narração.
 *
 *   node scripts/gravar-demo.mjs --ensaio && node scripts/gravar-demo.mjs
 */
const ENSAIO = process.argv.includes('--ensaio')

/** CSS e funções do palco. Reinjetado a cada navegação. */
const PALCO = `
(() => {
  if (window.__palco) return
  const estilo = document.createElement('style')
  estilo.textContent = \`
    #palco-legenda {
      position: fixed; left: 50%; bottom: 46px; transform: translateX(-50%);
      z-index: 2147483000; max-width: 1180px; padding: 18px 30px;
      background: rgba(8, 20, 18, .92); color: #f2f7f4; border-radius: 14px;
      font: 500 27px/1.4 system-ui, sans-serif; text-align: center;
      box-shadow: 0 18px 50px rgba(0,0,0,.45); backdrop-filter: blur(8px);
      border: 1px solid rgba(120, 220, 200, .28);
      opacity: 0; transition: opacity .35s ease;
      pointer-events: none; letter-spacing: -.01em;
    }
    #palco-legenda.aparece { opacity: 1; }
    #palco-legenda b { color: #5ed3b8; font-weight: 700; }
    #palco-cartela {
      position: fixed; inset: 0; z-index: 2147483001; display: grid;
      place-content: center; gap: 18px; text-align: center;
      background: linear-gradient(150deg, #071613 0%, #0d3a32 55%, #0a2420 100%);
      color: #f2f7f4; opacity: 0; transition: opacity .5s ease;
      pointer-events: none; padding: 0 8vw;
    }
    #palco-cartela.aparece { opacity: 1; }
    #palco-cartela .eyebrow {
      font: 600 20px/1 system-ui, sans-serif; letter-spacing: .32em;
      text-transform: uppercase; color: #5ed3b8;
    }
    #palco-cartela h1 {
      font: 800 78px/1.05 system-ui, sans-serif; margin: 0;
      letter-spacing: -.03em; max-width: 18ch;
    }
    #palco-cartela p {
      font: 400 30px/1.45 system-ui, sans-serif; margin: 0; color: #b9d6cd;
      max-width: 30ch; justify-self: center;
    }
    #palco-cartela .marca {
      display: inline-grid; place-items: center; width: 84px; height: 84px;
      border-radius: 22px; background: #0f9c82; color: #04201b;
      font: 800 38px/1 system-ui, sans-serif; justify-self: center;
    }
    #palco-cursor {
      position: fixed; z-index: 2147483002; width: 26px; height: 26px;
      margin: -13px 0 0 -13px; border-radius: 50%;
      background: rgba(94, 211, 184, .35); border: 2px solid #5ed3b8;
      box-shadow: 0 0 0 6px rgba(94, 211, 184, .14);
      transition: left .6s cubic-bezier(.4,0,.2,1), top .6s cubic-bezier(.4,0,.2,1);
      pointer-events: none; opacity: 0;
    }
    #palco-cursor.aparece { opacity: 1; }
    #palco-cursor.clique { transform: scale(.55); transition: transform .12s ease; }
    .palco-halo {
      position: fixed; z-index: 2147482999; border-radius: 12px;
      border: 3px solid #5ed3b8; box-shadow: 0 0 0 9999px rgba(6, 18, 16, .55);
      transition: all .45s cubic-bezier(.4,0,.2,1); pointer-events: none;
    }
  \`
  document.head.appendChild(estilo)

  const legenda = document.createElement('div')
  legenda.id = 'palco-legenda'
  const cartela = document.createElement('div')
  cartela.id = 'palco-cartela'
  const cursor = document.createElement('div')
  cursor.id = 'palco-cursor'
  document.body.append(legenda, cartela, cursor)

  let halo = null

  window.__palco = {
    legenda(texto) {
      if (!texto) {
        legenda.classList.remove('aparece')
        return
      }
      legenda.innerHTML = texto
      legenda.classList.add('aparece')
    },
    cartela(eyebrow, titulo, linha, marca) {
      cartela.innerHTML = marca
        ? \`<span class="marca">iP</span><p class="eyebrow">\${eyebrow}</p><h1>\${titulo}</h1><p>\${linha}</p>\`
        : \`<p class="eyebrow">\${eyebrow}</p><h1>\${titulo}</h1><p>\${linha}</p>\`
      cartela.classList.add('aparece')
    },
    fecharCartela() {
      cartela.classList.remove('aparece')
    },
    mover(x, y) {
      cursor.classList.add('aparece')
      cursor.style.left = x + 'px'
      cursor.style.top = y + 'px'
    },
    clicar() {
      cursor.classList.add('clique')
      setTimeout(() => cursor.classList.remove('clique'), 220)
    },
    esconderCursor() {
      cursor.classList.remove('aparece')
    },
    destacar(caixa) {
      if (!halo) {
        halo = document.createElement('div')
        halo.className = 'palco-halo'
        document.body.appendChild(halo)
      }
      halo.style.left = caixa.x - 8 + 'px'
      halo.style.top = caixa.y - 8 + 'px'
      halo.style.width = caixa.width + 16 + 'px'
      halo.style.height = caixa.height + 16 + 'px'
      halo.style.opacity = '1'
    },
    apagarDestaque() {
      if (halo) halo.style.opacity = '0'
    },
  }
})()
`

async function palco(pagina) {
  await pagina.evaluate(PALCO).catch(() => undefined)
}

const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ENSAIO ? 0 : ms))

/**
 * Mostra a fala, guarda o áudio dela e segura a cena pelo tempo da locução.
 *
 * O tempo de cada cena vem da duração real do wav, não de um número escrito na
 * mão: assim a voz nunca é cortada na virada da cena, e a legenda casa com o
 * que está sendo dito. Sem o modelo de voz instalado, cai no tempo estimado e o
 * vídeo sai mudo, como antes.
 */
async function narrar(pagina, texto, segundos = 3.6) {
  await palco(pagina)
  const limpo = texto.replace(/<[^>]+>/g, '')

  let audio = null
  let duracao = segundos
  if (comVoz) {
    const falado = await sintetizar(limpo)
    audio = path.relative(SAIDA, falado.arquivo)
    duracao = falado.duracao + RESPIRO
  }

  falas.push({ inicio: (Date.now() - inicio) / 1000, duracao, texto: limpo, audio })
  await pagina.evaluate((t) => window.__palco.legenda(t), texto)
  await esperar(duracao * 1000)
}

async function limparFala(pagina) {
  await pagina.evaluate(() => window.__palco?.legenda('')).catch(() => undefined)
}

async function cartela(pagina, eyebrow, titulo, linha, { marca = false, segundos = 3.2 } = {}) {
  await palco(pagina)

  let audio = null
  let duracao = segundos
  if (comVoz) {
    const falado = await sintetizar(`${titulo}. ${linha}`)
    audio = path.relative(SAIDA, falado.arquivo)
    duracao = Math.max(segundos, falado.duracao + RESPIRO)
  }

  falas.push({
    inicio: (Date.now() - inicio) / 1000,
    duracao,
    texto: `${titulo}. ${linha}`,
    cartela: true,
    audio,
  })
  await pagina.evaluate(
    ([e, t, l, m]) => window.__palco.cartela(e, t, l, m),
    [eyebrow, titulo, linha, marca],
  )
  await esperar(duracao * 1000)
  await pagina.evaluate(() => window.__palco.fecharCartela())
  await esperar(600)
}

/** Leva o cursor até o elemento, destaca e clica de verdade. */
async function apontar(pagina, alvo, { destacar = true, pausa = 900 } = {}) {
  const elemento = typeof alvo === 'string' ? pagina.locator(alvo).first() : alvo
  await elemento.scrollIntoViewIfNeeded().catch(() => undefined)
  const caixa = await elemento.boundingBox()
  if (!caixa) return elemento

  await palco(pagina)
  await pagina.evaluate(
    ([x, y]) => window.__palco.mover(x, y),
    [caixa.x + caixa.width / 2, caixa.y + caixa.height / 2],
  )
  if (destacar) await pagina.evaluate((c) => window.__palco.destacar(c), caixa)
  await esperar(pausa)
  return elemento
}

async function clicar(pagina, alvo, { pausa = 900, apos = 1100 } = {}) {
  const elemento = await apontar(pagina, alvo, { pausa })
  await pagina.evaluate(() => window.__palco.clicar())
  await elemento.click({ timeout: 15000 })
  await pagina.evaluate(() => window.__palco?.apagarDestaque()).catch(() => undefined)
  await esperar(apos)
  await palco(pagina)
}

async function digitar(pagina, alvo, texto, { atraso = 55 } = {}) {
  const elemento = await apontar(pagina, alvo, { pausa: 500 })
  await elemento.click()
  await elemento.fill('')
  await elemento.type(texto, { delay: atraso })
  await pagina.evaluate(() => window.__palco?.apagarDestaque()).catch(() => undefined)
  await esperar(700)
}

/** Campo de data não aceita digitação caractere a caractere. */
async function preencherData(pagina, alvo, valor) {
  const elemento = await apontar(pagina, alvo, { pausa: 600 })
  await elemento.fill(valor)
  await pagina.evaluate(() => window.__palco?.apagarDestaque()).catch(() => undefined)
  await esperar(600)
}

async function irPara(pagina, rotulo) {
  await clicar(pagina, `nav a:has-text("${rotulo}")`, { apos: 1600 })
  await palco(pagina)
}

async function principal() {
  if (!ENSAIO) {
    await rm(BRUTO, { recursive: true, force: true })
    await mkdir(BRUTO, { recursive: true })
  }

  // O Chromium também usa VRAM, e a locução roda na mesma placa: com os dois
  // disputando os 4 GB, a síntese falhava no meio da gravação. A tela é
  // renderizada por software, o que não muda o vídeo gravado.
  const navegador = await chromium.launch({
    args: ['--force-device-scale-factor=1', '--disable-gpu', '--disable-software-rasterizer'],
  })
  const contexto = await navegador.newContext({
    // Grava em 1600x900 e a montagem amplia para 1080p: a interface fica 20%
    // maior no vídeo final, legível em tela cheia e em celular.
    viewport: { width: 1600, height: 900 },
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    ...(ENSAIO ? {} : { recordVideo: { dir: BRUTO, size: { width: 1600, height: 900 } } }),
    baseURL: BASE,
  })
  await contexto.addInitScript(PALCO)

  const pagina = await contexto.newPage()
  inicio = Date.now()

  await roteiro(pagina)

  await pagina.close()
  await contexto.close()
  await navegador.close()

  if (!ENSAIO) {
    await writeFile(path.join(SAIDA, 'narracao.json'), JSON.stringify(falas, null, 2), 'utf8')
  }
  encerrarVoz()
  if (ENSAIO) {
    console.log(`Ensaio: ${falas.length} falas sintetizadas e guardadas em cache.`)
    return
  }
  console.log(
    `Falas registradas: ${falas.length}` +
      (comVoz ? ` (locução por ${motorDeVoz()})` : ' (sem locução)'),
  )
  console.log(`Duração aproximada: ${Math.round((Date.now() - inicio) / 1000)}s`)
}

async function roteiro(pagina) {
  // ---------------------------------------------------------------- abertura
  await pagina.goto('/login')
  await esperar(1200)
  await palco(pagina)
  await cartela(
    pagina,
    'Gestão imobiliária',
    'ImobiPro',
    'Da captação ao repasse do aluguel, sem planilha paralela.',
    { marca: true, segundos: 4.2 },
  )

  await narrar(
    pagina,
    'Uma imobiliária perde dinheiro em três lugares: <b>lead sem resposta</b>, <b>contrato sem controle</b> e <b>repasse feito no susto</b>.',
    5.2,
  )
  await narrar(
    pagina,
    'O ImobiPro resolve os três na mesma base. É isso que você vai ver agora, no sistema rodando.',
    4.6,
  )

  // ------------------------------------------------------------------ acesso
  await narrar(
    pagina,
    'Cada imobiliária tem seu próprio espaço, com equipe e permissões separadas.',
    3.8,
  )
  await digitar(pagina, 'input[type="email"]', CONTA.email, { atraso: 35 })
  await digitar(pagina, 'input[type="password"]', CONTA.senha, { atraso: 30 })
  await clicar(pagina, 'button:has-text("Entrar")', { apos: 2600 })

  const sair = pagina.getByRole('button', { name: 'Sair do tutorial' })
  if (await sair.isVisible().catch(() => false)) await sair.click()
  await esperar(800)
  await palco(pagina)

  // --------------------------------------------------------------- dashboard
  await cartela(
    pagina,
    'Módulo 1',
    'O dia começa aqui',
    'Um painel que responde: quanto entra este mês?',
  )
  await narrar(
    pagina,
    'Resultado do mês, a receber, inadimplência e carteira à venda. Tudo calculado no servidor, em tempo real.',
    4.6,
  )
  await apontar(pagina, '[data-tour="kpis"]', { pausa: 2600 })
  await limparFala(pagina)

  await narrar(
    pagina,
    'E, logo abaixo, <b>o que trava dinheiro se ficar parado</b>: lead sem contato, visita do dia, cobrança vencida.',
    4.8,
  )
  await apontar(pagina, '[data-tour="precisa-hoje"]', { pausa: 2400 })
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await limparFala(pagina)

  // ----------------------------------------------------------------- imóveis
  await cartela(
    pagina,
    'Módulo 2',
    'A carteira',
    'Captar, publicar e achar o imóvel que o cliente pediu.',
  )
  await irPara(pagina, 'Imóveis')
  await narrar(
    pagina,
    'A carteira inteira em cards, tabela ou mapa. A mesma busca, três leituras.',
    4.2,
  )

  await narrar(
    pagina,
    'No cadastro de pessoas, a foto é opcional: ajuda a reconhecer quem chega para assinar, e nunca trava o cadastro.',
    5.4,
  )
  await limparFala(pagina)

  await narrar(pagina, 'A busca entende a pergunta do cliente, não só o código do imóvel.', 3.6)
  await digitar(pagina, 'input[placeholder*="código"]', 'cobertura vista livre', { atraso: 60 })
  await esperar(2200)
  await narrar(
    pagina,
    'Busca por texto direto no banco, com índice. Responde enquanto o cliente está na linha.',
    4.4,
  )
  await digitar(pagina, 'input[placeholder*="código"]', '', { atraso: 10 })
  await esperar(1400)

  await narrar(pagina, 'Precisa responder "o que você tem neste bairro?" Abre o mapa.', 3.8)
  await clicar(pagina, 'button:has-text("Mapa")', { apos: 3200 })
  await esperar(2600)
  await clicar(pagina, 'button:has-text("Cards")', { apos: 1800 })
  await limparFala(pagina)

  await narrar(
    pagina,
    'Na ficha do imóvel: valores, características, galeria e o histórico de tudo que mudou.',
    4.4,
  )
  await clicar(pagina, '.grid a >> nth=1', { apos: 2600 })
  await esperar(1400)
  await clicar(pagina, 'button:has-text("Fotos e mídia")', { apos: 2200 })
  await narrar(
    pagina,
    'A primeira foto é a capa do anúncio. Publicar exige cinco fotos: é regra do sistema, não do corretor.',
    4.6,
  )
  await clicar(pagina, 'button:has-text("Histórico")', { apos: 2200 })
  await narrar(
    pagina,
    'Mudou valor, situação ou publicação? Fica registrado com autor e data. Nada some.',
    4.4,
  )
  await limparFala(pagina)

  // ------------------------------------------------------------ site público
  await cartela(
    pagina,
    'Módulo 3',
    'O site do cliente',
    'A mesma base alimenta a vitrine que o interessado vê.',
  )
  await narrar(
    pagina,
    'Do painel, um clique abre o site que o cliente enxerga. É a mesma carteira, publicada.',
    4.6,
  )
  await apontar(pagina, '[data-tour="ver-site"]', { pausa: 2200 })
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await pagina.goto(SITE)
  await esperar(2400)
  await palco(pagina)

  await narrar(
    pagina,
    'O catálogo se organiza sozinho por finalidade, tipo, bairro e faixa de aluguel, com a contagem de cada prateleira.',
    5.4,
  )
  await esperar(1200)
  await clicar(pagina, 'main a[href*="/imovel/"] >> nth=0', { apos: 2600 })
  await narrar(
    pagina,
    'Na ficha, galeria, vídeo, planta e o mapa de verdade, com o pino no endereço do imóvel.',
    4.8,
  )
  await esperar(2000)
  await clicar(pagina, 'text=Onde fica', { apos: 2200 })
  await esperar(1800)
  await limparFala(pagina)

  await narrar(
    pagina,
    'E o pedido de visita não exige cadastro: o interessado deixa o contato e recebe um protocolo.',
    5.0,
  )
  await digitar(pagina, 'aside input >> nth=0', 'Marina Interessada', { atraso: 45 })
  await digitar(pagina, 'aside input >> nth=1', '35991234567', { atraso: 40 })
  await esperar(1200)
  await limparFala(pagina)

  await narrar(
    pagina,
    'Do outro lado, esse pedido vira ticket com analista responsável e prazo de trinta minutos para o primeiro contato.',
    5.6,
  )
  await pagina.goto('/atendimento')
  await esperar(2600)
  await palco(pagina)
  await limparFala(pagina)

  // --------------------------------------------------------------------- CRM
  await cartela(
    pagina,
    'Módulo 4',
    'O funil',
    'Lead atendido em 15 minutos e o sistema cobra isso.',
  )
  await irPara(pagina, 'Funil de vendas')
  await narrar(
    pagina,
    'Leads do site e dos portais entram sozinhos e já saem distribuídos para um corretor ativo.',
    4.6,
  )
  await apontar(pagina, '[data-tour="metricas-funil"]', { pausa: 2600 })
  await narrar(
    pagina,
    'O SLA de primeiro contato é o diferencial: 15 minutos. Estourou, o cartão pisca em vermelho.',
    4.8,
  )
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await limparFala(pagina)

  await narrar(
    pagina,
    'Mover o lead é arrastar o cartão. Ao perder, o sistema exige o motivo. É ele que vira relatório.',
    5.0,
  )
  const cartao = pagina.locator('[data-tour="kanban"] div[draggable="true"]').first()
  const coluna = pagina.locator('[data-tour="kanban"] section').nth(1)
  await apontar(pagina, cartao, { pausa: 900 })
  await cartao.dragTo(coluna).catch(() => undefined)
  await esperar(2200)
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await limparFala(pagina)

  await narrar(
    pagina,
    'Dentro do lead, a linha do tempo: cada ligação, visita e proposta fica registrada.',
    4.4,
  )
  await clicar(pagina, '[data-tour="kanban"] div[draggable="true"]', { apos: 2800 })
  await esperar(2400)
  await limparFala(pagina)

  // --------------------------------------------------------------- contratos
  await cartela(pagina, 'Módulo 5', 'O contrato', 'Assinou? O sistema faz o resto sozinho.')
  await irPara(pagina, 'Contratos')
  await narrar(
    pagina,
    'Locação e venda, numerados por ano, com filtro do que vence nos próximos 90 dias.',
    4.4,
  )
  await clicar(pagina, 'table tbody tr', { apos: 2800 })
  await narrar(
    pagina,
    'Ao ativar, o imóvel sai do mercado, as comissões nascem com o percentual congelado e as cobranças do período são geradas.',
    5.6,
  )
  await esperar(1200)
  await narrar(
    pagina,
    'Reajuste anual com prévia antes de aplicar, e rescisão com multa proporcional calculada.',
    4.6,
  )
  await limparFala(pagina)

  // -------------------------------------------------------------- financeiro
  await cartela(pagina, 'Módulo 6', 'O dinheiro', 'Receber, conciliar e repassar sem planilha.')
  await irPara(pagina, 'Contas a receber')
  await narrar(
    pagina,
    'As cobranças nascem dez dias antes do vencimento. Atrasou, a régua dispara sozinha.',
    4.6,
  )
  await apontar(pagina, '[data-tour="inadimplencia"]', { pausa: 2400 })
  await narrar(
    pagina,
    'Lembrete, cobrança, aviso formal e jurídico, nessa ordem, sem ninguém precisar lembrar.',
    4.6,
  )
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await limparFala(pagina)

  await narrar(
    pagina,
    'A baixa pode ser uma a uma ou em lote, pelo arquivo de retorno do banco.',
    4.2,
  )
  await apontar(pagina, '[data-tour="conciliar"]', { pausa: 2400 })
  await pagina.evaluate(() => window.__palco.apagarDestaque())
  await limparFala(pagina)

  await irPara(pagina, 'Repasses')
  await narrar(
    pagina,
    'Recebeu do inquilino, o repasse do proprietário aparece aqui: aluguel menos taxa e retenções.',
    4.8,
  )
  await narrar(
    pagina,
    'Condomínio e IPTU não entram no resultado da imobiliária. É dinheiro de terceiros, e o sistema sabe disso.',
    5.2,
  )
  await limparFala(pagina)

  await irPara(pagina, 'Comissões')
  await narrar(
    pagina,
    'Comissão por contrato, com rateio entre captador, vendedor e imobiliária.',
    4.2,
  )
  await limparFala(pagina)

  // --------------------------------------------------------------- vistorias
  await cartela(pagina, 'Módulo 7', 'A vistoria', 'A prova que evita briga na saída.')
  await irPara(pagina, 'Vistorias')
  await narrar(
    pagina,
    'Checklist por cômodo, foto pelo celular e laudo em PDF assinado pelas duas partes.',
    4.6,
  )
  await clicar(pagina, 'table tbody tr', { apos: 2800 })
  await narrar(
    pagina,
    'Na saída, o sistema compara item a item com a entrada e aponta o que mudou.',
    4.4,
  )
  await esperar(1600)
  await limparFala(pagina)

  // -------------------------------------------------------------- relatórios
  await cartela(
    pagina,
    'Módulo 8',
    'A prestação de contas',
    'Números que o dono da imobiliária cobra.',
  )
  await irPara(pagina, 'Relatórios')
  await narrar(
    pagina,
    'Receita contra despesa, origem dos leads, motivo das perdas e desempenho por corretor.',
    4.6,
  )
  await preencherData(pagina, 'input[type="date"] >> nth=0', '2026-01-01')
  await clicar(pagina, 'button:has-text("Atualizar")', { apos: 2600 })
  await narrar(
    pagina,
    'O ano inteiro em uma tela, com o aluguel de terceiros fora do resultado da imobiliária.',
    5.0,
  )
  await esperar(2200)
  await limparFala(pagina)

  // ---------------------------------------------------- portal do inquilino
  await cartela(
    pagina,
    'Módulo 9',
    'Depois da assinatura',
    'O inquilino resolve sozinho o que hoje chega por WhatsApp.',
  )
  await narrar(
    pagina,
    'Assinado o contrato, a imobiliária libera o acesso do inquilino em um clique.',
    4.4,
  )
  await narrar(
    pagina,
    'Ele vê o próprio contrato, os boletos com Pix, abre chamado de manutenção e assina o laudo de vistoria. E não alcança o painel da imobiliária.',
    6.4,
  )
  await limparFala(pagina)

  // ------------------------------------------------------------- onboarding
  await cartela(
    pagina,
    'Adoção',
    'A equipe aprende sozinha',
    'Tutorial guiado com missões conferidas no sistema.',
  )
  await clicar(pagina, 'button:has-text("Tutorial")', { apos: 2200 })
  await narrar(
    pagina,
    'O maior risco de um sistema novo não é o preço: é a equipe não usar.',
    4.4,
  )
  await narrar(
    pagina,
    'Doze missões, cinco trilhas e níveis. E a missão só é dada como cumprida quando o trabalho aparece no banco.',
    5.2,
  )
  await esperar(1800)
  await pagina.keyboard.press('Escape')
  await esperar(1200)
  await limparFala(pagina)

  // -------------------------------------------------------------- segurança
  await cartela(
    pagina,
    'Controle',
    'Cada um vê o que é dele',
    'Permissão por papel, isolada no banco.',
  )
  await narrar(
    pagina,
    'O corretor não enxerga o financeiro. Nem no menu, nem digitando o endereço na mão.',
    4.6,
  )
  await limparFala(pagina)

  await cartela(
    pagina,
    'Qualidade comprovada',
    '589 testes automatizados',
    '0 bug · 0 vulnerabilidade · nota A em confiabilidade, segurança e manutenção',
    { segundos: 5.0 },
  )

  await cartela(
    pagina,
    'ImobiPro',
    'Comece pela sua carteira real',
    'Implantação em dias, sem migrar para planilha nenhuma.',
    { marca: true, segundos: 5.0 },
  )
}

principal().catch((erro) => {
  console.error(erro)
  process.exit(1)
})
