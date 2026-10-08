/**
 * Monta o vídeo final a partir da gravação bruta.
 *
 *   node scripts/montar-demo.mjs
 *
 * Entra: midia/bruto/*.webm + midia/narracao.json (gerados por gravar-demo.mjs).
 * Sai: midia/imobipro-apresentacao.mp4, .srt (legenda) e o poster de capa.
 *
 * O vídeo é gravado em 1600x900 e ampliado para 1080p assim a interface fica
 * legível em tela cheia e no celular.
 *
 * O áudio tem duas camadas: a locução de cada fala, colocada no instante em que
 * a fala apareceu na tela, e a trilha por baixo, bem mais baixa e abaixada de
 * novo enquanto a voz fala. Sem o modelo de voz e sem a trilha, sai uma faixa
 * silenciosa: algumas redes recusam vídeo sem áudio nenhum.
 */

import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MIDIA = path.join(RAIZ, 'midia')
const BRUTO = path.join(MIDIA, 'bruto')

const origem = path.join(
  BRUTO,
  readdirSync(BRUTO).find((f) => f.endsWith('.webm')),
)
const TRILHA = path.join(MIDIA, 'trilha', 'corporate-company-introduction.mp3')
const destino = path.join(MIDIA, 'imobipro-apresentacao.mp4')
const legenda = path.join(MIDIA, 'imobipro-apresentacao.srt')
const poster = path.join(MIDIA, 'imobipro-capa.jpg')

const duracao = Number(
  execFileSync('ffprobe', [
    '-v',
    'error',
    '-show_entries',
    'format=duration',
    '-of',
    'csv=p=0',
    origem,
  ])
    .toString()
    .trim(),
)

console.log(`Gravação bruta: ${duracao.toFixed(1)}s`)

const falas = JSON.parse(readFileSync(path.join(MIDIA, 'narracao.json'), 'utf8'))
const locucoes = falas.filter((fala) => fala.audio && existsSync(path.join(MIDIA, fala.audio)))
const comTrilha = existsSync(TRILHA)

/**
 * Monta a faixa de áudio.
 *
 * Cada locução entra atrasada até o segundo em que a legenda apareceu, o que
 * mantém voz, texto e tela contando a mesma coisa. A trilha entra por último,
 * em volume de fundo, e o sidechain a abaixa sozinha quando a voz começa.
 */
function filtroDeAudio() {
  if (!locucoes.length && !comTrilha) return null

  const partes = []
  const rotulos = []

  locucoes.forEach((fala, indice) => {
    const atraso = Math.max(0, Math.round(fala.inicio * 1000))
    partes.push(`[${indice + 1}:a]adelay=${atraso}|${atraso},apad[v${indice}]`)
    rotulos.push(`[v${indice}]`)
  })

  if (rotulos.length) {
    partes.push(
      `${rotulos.join('')}amix=inputs=${rotulos.length}:normalize=0:dropout_transition=0,` +
        `atrim=0:${duracao.toFixed(2)},volume=1.1[voz]`,
    )
  }

  if (!comTrilha) return { filtro: partes.join(';'), saida: '[voz]' }

  const entradaTrilha = locucoes.length + 1
  partes.push(
    `[${entradaTrilha}:a]aloop=loop=-1:size=2e9,atrim=0:${duracao.toFixed(2)},` +
      `volume=0.16,afade=t=in:st=0:d=2,afade=t=out:st=${(duracao - 3).toFixed(2)}:d=3[trilha]`,
  )

  if (!rotulos.length) return { filtro: partes.join(';'), saida: '[trilha]' }

  // Sidechain: a trilha baixa sozinha enquanto a locução fala e volta depois.
  partes.push(`[voz]asplit=2[voz1][chave]`)
  partes.push(
    `[trilha][chave]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=600[trilhabaixa]`,
  )
  // Limitador no fim, depois da soma: é a soma que pode estourar, não a voz.
  partes.push(
    `[voz1][trilhabaixa]amix=inputs=2:normalize=0,alimiter=limit=0.85:level=disabled[mix]`,
  )
  return { filtro: partes.join(';'), saida: '[mix]' }
}

const audio = filtroDeAudio()

const entradas = ['-i', origem]
for (const fala of locucoes) entradas.push('-i', path.join(MIDIA, fala.audio))
if (comTrilha) entradas.push('-i', TRILHA)
if (!audio) {
  entradas.push('-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000')
}

const argumentos = [
  '-y',
  ...entradas,
  '-filter_complex',
  audio
    ? `${audio.filtro};[0:v]scale=1920:1080:flags=lanczos,fps=30,fade=t=in:st=0:d=0.8,fade=t=out:st=${(duracao - 1.2).toFixed(2)}:d=1.2[video]`
    : `[0:v]scale=1920:1080:flags=lanczos,fps=30,fade=t=in:st=0:d=0.8,fade=t=out:st=${(duracao - 1.2).toFixed(2)}:d=1.2[video]`,
  '-map',
  '[video]',
  '-map',
  audio ? audio.saida : '1:a',
  '-c:v',
  'libx264',
  '-preset',
  'slow',
  '-crf',
  '20',
  '-pix_fmt',
  'yuv420p',
  '-c:a',
  'aac',
  '-b:a',
  '160k',
  '-ar',
  '48000',
  '-shortest',
  '-movflags',
  '+faststart',
  destino,
]

console.log(
  `Áudio: ${locucoes.length} locuções${comTrilha ? ' com trilha de fundo' : ' sem trilha'}`,
)
execFileSync('ffmpeg', argumentos, { stdio: ['ignore', 'ignore', 'inherit'] })

// ------------------------------------------------------------------ legenda

const relogio = (segundos) => {
  const total = Math.max(0, segundos)
  const h = String(Math.floor(total / 3600)).padStart(2, '0')
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const s = String(Math.floor(total % 60)).padStart(2, '0')
  const ms = String(Math.round((total % 1) * 1000)).padStart(3, '0')
  return `${h}:${m}:${s},${ms}`
}

const srt = falas
  .map((fala, indice) => {
    const fim = fala.inicio + fala.duracao
    return `${indice + 1}\n${relogio(fala.inicio)} --> ${relogio(fim)}\n${fala.texto}\n`
  })
  .join('\n')
writeFileSync(legenda, srt, 'utf8')

// ---------------------------------------------------------- roteiro de fala

const minutos = (segundos) => {
  const m = String(Math.floor(segundos / 60)).padStart(2, '0')
  const s = String(Math.floor(segundos % 60)).padStart(2, '0')
  return `${m}:${s}`
}

const motor = locucoes.length ? 'Chatterbox pt-BR' : 'sem locução'
const total = `${Math.floor(duracao / 60)}min${String(Math.round(duracao % 60)).padStart(2, '0')}s`
const roteiro =
  `# Roteiro de locução do vídeo de apresentação\n\n` +
  `Vídeo: \`midia/imobipro-apresentacao.mp4\` · ${total} · 1080p · locução sintetizada` +
  ` (${motor}) e trilha CC0.\n\n` +
  `As falas abaixo são as que estão no áudio e na legenda \`imobipro-apresentacao.srt\`.\n` +
  `Para regravar com voz humana, siga os tempos: a cadência do vídeo foi montada\n` +
  `a partir da duração de cada fala.\n\n` +
  `**Tom:** direto, de igual para igual com dono de imobiliária. Nada de superlativo\n` +
  `("revolucionário", "incrível"). Cada frase afirma algo que a tela está provando.\n\n` +
  `| Tempo | Tipo | Fala |\n|---|---|---|\n` +
  falas
    .map(
      (fala) =>
        `| ${minutos(fala.inicio)} | ${fala.cartela ? 'Cartela' : 'Narração'} | ${fala.texto} |`,
    )
    .join('\n') +
  `\n`
writeFileSync(path.join(MIDIA, 'roteiro-locucao.md'), roteiro, 'utf8')

// ------------------------------------------------------------------- poster

execFileSync(
  'ffmpeg',
  ['-y', '-ss', '2', '-i', destino, '-frames:v', '1', '-q:v', '2', poster],
  { stdio: ['ignore', 'ignore', 'inherit'] },
)

const tamanho = execFileSync('ffprobe', [
  '-v',
  'error',
  '-show_entries',
  'format=size',
  '-of',
  'csv=p=0',
  destino,
])
  .toString()
  .trim()

console.log(`Vídeo:   ${destino} (${(Number(tamanho) / 1e6).toFixed(1)} MB)`)
console.log(`Legenda: ${legenda} (${falas.length} entradas)`)
console.log(`Capa:    ${poster}`)
