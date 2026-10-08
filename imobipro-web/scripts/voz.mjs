/**
 * Narração do vídeo, sintetizada na máquina.
 *
 * Dois motores, nesta ordem:
 *
 * 1. Chatterbox (Resemble AI, MIT), checkpoint dedicado de português do Brasil.
 *    É o que soa como gente: modelo de 0,5B em GPU, com prosódia e respiração.
 * 2. Piper (MIT), modelo pequeno de CPU. Entra quando não há GPU ou ambiente
 *    Python preparado. Serve, mas soa sintético.
 *
 * Sem nenhum dos dois, a gravação segue muda e com os tempos estimados do
 * roteiro. Nada do texto sai da máquina em nenhum dos casos.
 *
 * Preparo (uma vez): `node scripts/baixar-midia-livre.mjs`.
 */

import { execFileSync, spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
export const PASTA_VOZ = path.join(RAIZ, 'midia', 'voz')
const CACHE = path.join(PASTA_VOZ, 'falas')

const PIPER_MODELO = process.env.PIPER_MODELO || path.join(PASTA_VOZ, 'pt_BR-faber-medium.onnx')
const PYTHON_PIPER = process.env.PYTHON || 'python3'

// O Chatterbox precisa de torch com CUDA, que não roda no Python do sistema.
// O ambiente fica fora do repositório, montado por baixar-midia-livre.mjs.
const CHATTERBOX_PYTHON =
  process.env.CHATTERBOX_PYTHON ||
  path.join(homedir(), '.cache', 'imobipro-tts', 'venv', 'bin', 'python')
const CHATTERBOX_MODELO =
  process.env.CHATTERBOX_MODELO ||
  path.join(homedir(), '.cache', 'imobipro-tts', 'chatterbox-pt-br')

// A voz embutida no modelo é inglesa: sem uma referência em português, o
// sotaque escorrega e frases longas chegam a trocar de idioma.
const REFERENCIA = process.env.VOZ_REFERENCIA || path.join(PASTA_VOZ, 'referencia-pt-br.wav')

/** Fala em áudio soa mal com marcação: o negrito é da legenda, não da voz. */
export function semMarcacao(texto) {
  return texto
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function temChatterbox() {
  return existsSync(CHATTERBOX_PYTHON) && existsSync(path.join(CHATTERBOX_MODELO, 've.pt'))
}

function temPiper() {
  return existsSync(PIPER_MODELO)
}

export function motorDeVoz() {
  if (temChatterbox()) return 'chatterbox'
  if (temPiper()) return 'piper'
  return null
}

export function vozDisponivel() {
  return motorDeVoz() !== null
}

export function duracaoDoAudio(arquivo) {
  const saida = execFileSync('ffprobe', [
    '-v',
    'error',
    '-show_entries',
    'format=duration',
    '-of',
    'csv=p=0',
    arquivo,
  ])
  return Number(saida.toString().trim())
}

/**
 * Processo do Chatterbox, vivo entre as falas.
 *
 * Subir o modelo custa dezenas de segundos; o roteiro tem mais de cinquenta
 * falas. O processo fica aberto e responde uma linha JSON por pedido.
 */
let servidor = null
let fila = Promise.resolve()
let falasNoServidor = 0

// A memória da GPU não volta inteira entre uma fala e outra: em uma placa de
// 4 GB o processo chega ao teto por volta da décima fala. Reiniciar custa uns
// vinte segundos e devolve a placa limpa.
const FALAS_POR_PROCESSO = Number(process.env.VOZ_FALAS_POR_PROCESSO || 6)

function abrirServidor() {
  if (servidor) return servidor

  const argumentos = [path.join(RAIZ, 'scripts', 'voz_servidor.py'), CHATTERBOX_MODELO]
  if (existsSync(REFERENCIA)) argumentos.push(REFERENCIA)

  const processo = spawn(CHATTERBOX_PYTHON, argumentos, {
    stdio: ['pipe', 'pipe', 'inherit'],
    // A GPU fragmenta ao longo de uma gravação inteira; segmentos expansíveis
    // evitam o "sem memória" que aparecia lá pela quadragésima fala.
    env: { ...process.env, PYTORCH_CUDA_ALLOC_CONF: 'expandable_segments:True' },
  })

  let restante = ''
  const pendentes = []

  processo.stdout.on('data', (pedaco) => {
    restante += pedaco.toString()
    let quebra = restante.indexOf('\n')
    while (quebra >= 0) {
      const linha = restante.slice(0, quebra).trim()
      restante = restante.slice(quebra + 1)
      // As bibliotecas do modelo escrevem avisos no stdout: só as linhas JSON
      // são resposta, o resto é ruído e vai para o log.
      if (linha) {
        let resposta = null
        try {
          resposta = JSON.parse(linha)
        } catch {
          process.stderr.write(`voz: ${linha}\n`)
        }
        if (resposta) pendentes.shift()?.(resposta)
      }
      quebra = restante.indexOf('\n')
    }
  })

  servidor = {
    processo,
    esperar: () => new Promise((resolver) => pendentes.push(resolver)),
    pedir(pedido) {
      const resposta = this.esperar()
      processo.stdin.write(`${JSON.stringify(pedido)}\n`)
      return resposta
    },
    pronto: null,
  }
  servidor.pronto = servidor.esperar()
  return servidor
}

export function encerrarVoz() {
  servidor?.processo.stdin.end()
  servidor = null
  falasNoServidor = 0
}

async function servidorPronto() {
  if (servidor && falasNoServidor >= FALAS_POR_PROCESSO) encerrarVoz()
  const servico = abrirServidor()
  await servico.pronto
  return servico
}

function arquivoDaFala(texto, motor) {
  const voz = motor === 'chatterbox' && existsSync(REFERENCIA) ? 'ref-ptbr-v3' : motor
  const chave = createHash('sha256').update(`${voz}|${texto}`).digest('hex').slice(0, 24)
  return path.join(CACHE, `${chave}.wav`)
}

/**
 * Sintetiza a fala e devolve o arquivo e a duração real.
 *
 * A duração real é o que manda no ritmo do vídeo: a cena espera o áudio
 * terminar, em vez de um tempo chutado que deixaria a voz cortada ou o silêncio
 * sobrando. O resultado fica em cache pelo hash do texto, então mexer em uma
 * frase só sintetiza aquela frase.
 */
export async function sintetizar(texto) {
  const limpo = semMarcacao(texto)
  const motor = motorDeVoz()
  if (!motor) throw new Error('Nenhum motor de voz disponível.')

  const arquivo = arquivoDaFala(limpo, motor)
  if (existsSync(arquivo)) {
    return { arquivo, duracao: duracaoDoAudio(arquivo), texto: limpo, motor }
  }
  mkdirSync(CACHE, { recursive: true })

  if (motor === 'piper') {
    execFileSync(PYTHON_PIPER, ['-m', 'piper', '-m', PIPER_MODELO, '-f', arquivo], {
      input: limpo,
      stdio: ['pipe', 'ignore', 'inherit'],
    })
    return { arquivo, duracao: duracaoDoAudio(arquivo), texto: limpo, motor }
  }

  // Uma fala por vez: o processo responde na ordem em que recebe.
  const promessa = fila.then(async () => {
    let servico = await servidorPronto()
    let resposta = await servico.pedir({ texto: limpo, arquivo })
    falasNoServidor += 1

    // Uma falha por memória some com o processo novo: vale uma segunda chance
    // antes de derrubar a gravação inteira por causa de uma frase.
    if (!resposta.ok && /memory|memória/i.test(resposta.erro ?? '')) {
      encerrarVoz()
      servico = await servidorPronto()
      resposta = await servico.pedir({ texto: limpo, arquivo })
      falasNoServidor += 1
    }

    if (!resposta.ok) throw new Error(`Falha ao sintetizar "${limpo}": ${resposta.erro}`)
    return { arquivo, duracao: resposta.duracao, texto: limpo, motor }
  })
  fila = promessa.catch(() => undefined)
  return promessa
}
