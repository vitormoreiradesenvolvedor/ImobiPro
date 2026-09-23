/**
 * Gera o PDF do deck comercial a partir do HTML.
 *
 *   node scripts/deck-pdf.mjs ../docs/comercial/deck-comercial.html ../docs/comercial/deck-comercial.pdf
 *
 * O PDF sai em paisagem, um slide por página, com as notas do apresentador
 * impressas embaixo de cada slide.
 */

import path from 'node:path'

import { chromium } from '@playwright/test'
const alvo = path.resolve(process.argv[2])
const saida = process.argv[3]
const navegador = await chromium.launch()
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 810 } })
await pagina.goto(`file://${alvo}`)
await pagina.waitForTimeout(1500)
await pagina.emulateMedia({ media: 'print' })
await pagina.pdf({
  path: saida,
  width: '1440px',
  height: '810px',
  printBackground: true,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
})
await navegador.close()
console.log('pdf gerado')
