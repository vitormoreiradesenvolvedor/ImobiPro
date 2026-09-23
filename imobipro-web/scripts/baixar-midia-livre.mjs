/**
 * Prepara o que o vídeo precisa e não cabe no repositório: voz e trilha.
 *
 *   node scripts/baixar-midia-livre.mjs
 *
 * Voz principal: Chatterbox (Resemble AI, MIT), checkpoint dedicado de
 * português do Brasil, rodando na GPU. É a voz que soa como gente.
 * Voz reserva: Piper pt-BR (MIT), cerca de 63 MB, roda em qualquer CPU.
 * Trilha: faixa CC0 do Freesound, obtida pela API do Openverse.
 *
 * O ambiente Python do Chatterbox fica em ~/.cache/imobipro-tts, fora do
 * repositório: são alguns gigabytes de torch com CUDA. Tudo aqui é idempotente,
 * o que já existe não é refeito.
 */

import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MIDIA = path.join(RAIZ, 'midia')
const PASTA_VOZ = path.join(MIDIA, 'voz')
const PASTA_TRILHA = path.join(MIDIA, 'trilha')

const VOZ =
  'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx'

const TRILHA = {
  arquivo: 'corporate-company-introduction.mp3',
  url: 'https://cdn.freesound.org/previews/524/524308_6714882-hq.mp3',
  titulo: 'Corporate company introduction video',
  autor: 'Bertsz',
  licenca: 'CC0 1.0',
  origem: 'https://freesound.org/people/Bertsz/sounds/524308',
}

async function baixar(url, destino) {
  if (existsSync(destino)) {
    console.log(`já existe: ${path.relative(RAIZ, destino)}`)
    return
  }
  console.log(`baixando: ${path.relative(RAIZ, destino)}`)
  const resposta = await fetch(url, { headers: { 'User-Agent': 'ImobiPro/1.0' } })
  if (!resposta.ok) throw new Error(`${resposta.status} ao baixar ${url}`)
  writeFileSync(destino, Buffer.from(await resposta.arrayBuffer()))
}

mkdirSync(PASTA_VOZ, { recursive: true })
mkdirSync(PASTA_TRILHA, { recursive: true })

await baixar(VOZ, path.join(PASTA_VOZ, 'pt_BR-faber-medium.onnx'))
await baixar(`${VOZ}.json`, path.join(PASTA_VOZ, 'pt_BR-faber-medium.onnx.json'))
await baixar(TRILHA.url, path.join(PASTA_TRILHA, TRILHA.arquivo))

writeFileSync(
  path.join(PASTA_TRILHA, 'CREDITOS.md'),
  `# Trilha do vídeo\n\n` +
    `| Faixa | Autor | Licença | Origem |\n|---|---|---|---|\n` +
    `| ${TRILHA.titulo} | ${TRILHA.autor} | ${TRILHA.licenca} | ${TRILHA.origem} |\n\n` +
    `Licença CC0 permite uso comercial sem atribuição obrigatória. A tabela\n` +
    `existe para provar a procedência antes de publicar material comercial.\n`,
  'utf8',
)

try {
  execFileSync('python3', ['-c', 'import piper'], { stdio: 'ignore' })
  console.log('piper: instalado')
} catch {
  console.log('piper ausente: instale com "python3 -m pip install --user piper-tts"')
}

// ------------------------------------------------------------- Chatterbox

const BASE_TTS = path.join(homedir(), '.cache', 'imobipro-tts')
const PYTHON_TTS = path.join(BASE_TTS, 'venv', 'bin', 'python')
const MODELO_TTS = path.join(BASE_TTS, 'chatterbox-pt-br')

function rodar(programa, argumentos) {
  const saida = spawnSync(programa, argumentos, { stdio: 'inherit' })
  if (saida.status !== 0) throw new Error(`${programa} falhou`)
}

function temUv() {
  return spawnSync('uv', ['--version'], { stdio: 'ignore' }).status === 0
}

if (existsSync(path.join(MODELO_TTS, 've.pt'))) {
  console.log('chatterbox: já preparado')
} else if (!temUv()) {
  console.log(
    'chatterbox pulado: instale o uv (https://docs.astral.sh/uv/) e rode este script de novo.\n' +
      'Sem ele o vídeo usa a voz do Piper.',
  )
} else {
  console.log('preparando o ambiente do Chatterbox (alguns GB, demora na primeira vez)')
  mkdirSync(BASE_TTS, { recursive: true })
  if (!existsSync(PYTHON_TTS)) {
    rodar('uv', ['venv', '--python', '3.12', path.join(BASE_TTS, 'venv')])
  }
  // torch para Python 3.12 com CUDA; librosa, setuptools e coverage nas versões
  // que a marca d'água do Chatterbox ainda consegue importar.
  rodar('uv', [
    'pip',
    'install',
    '--python',
    PYTHON_TTS,
    'torch',
    'torchaudio',
    '--torch-backend=cu124',
  ])
  rodar('uv', [
    'pip',
    'install',
    '--python',
    PYTHON_TTS,
    'chatterbox-tts',
    'setuptools<81',
    'librosa==0.11.0',
    'coverage>=7.6',
  ])

  const baixarModelo = `
import os, pathlib
from huggingface_hub import snapshot_download
base = snapshot_download('ResembleAI/chatterbox', allow_patterns=['ve.pt', 's3gen.pt', 'conds.pt', 'Cangjie5_TC.json'])
ptbr = snapshot_download('ResembleAI/Chatterbox-Multilingual-pt-br')
destino = pathlib.Path(${JSON.stringify(MODELO_TTS)})
destino.mkdir(parents=True, exist_ok=True)
ligacoes = {
    've.pt': f'{base}/ve.pt',
    'conds.pt': f'{base}/conds.pt',
    'Cangjie5_TC.json': f'{base}/Cangjie5_TC.json',
    # O decoder v3 do pacote pt-BR não casa com esta versão do chatterbox-tts.
    's3gen.pt': f'{base}/s3gen.pt',
    't3_mtl23ls_v2.safetensors': f'{ptbr}/t3_pt_br.safetensors',
    'grapheme_mtl_merged_expanded_v1.json': f'{ptbr}/grapheme_mtl_merged_expanded_v1.json',
}
for nome, origem in ligacoes.items():
    alvo = destino / nome
    if alvo.exists() or alvo.is_symlink():
        alvo.unlink()
    os.symlink(origem, alvo)
print('modelo pronto em', destino)
`
  rodar(PYTHON_TTS, ['-c', baixarModelo])
}

console.log('pronto.')
