import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  // Obrigatório: o refresh token viaja em cookie HttpOnly.
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

let accessToken = null

// Cada login/logout abre uma "geração" de sessão. Uma resposta 401 que chega
// atrasada pertence à geração anterior e não pode derrubar quem acabou de
// entrar era o que acontecia ao trocar de usuário.
let geracao = 0

export const definirAccessToken = (token) => {
  accessToken = token
  geracao += 1
}

// O WebSocket de notificações precisa do mesmo access token; ele vive só em
// memória (nunca em localStorage) e é lido daqui.
export const obterAccessToken = () => accessToken

http.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  config._geracao = geracao
  return config
})

// Uma renovação por vez: requisições que falharem durante o refresh ficam na
// fila e são repetidas com o token novo.
let renovando = null
const fila = []

const aoRenovar = (token) => {
  fila.splice(0).forEach((resolver) => resolver(token))
}

/**
 * Renova a sessão pelo cookie HttpOnly, uma chamada por vez.
 *
 * O refresh token gira a cada uso: duas renovações concorrentes fariam a
 * segunda mandar um token que a primeira acabou de invalidar, e a sessão cairia
 * sozinha. Por isso o boot da SPA e o interceptador compartilham esta promessa
 * em vez de cada um chamar a API por conta própria.
 */
export function renovarSessao({ avisarSeFalhar = false } = {}) {
  if (renovando) return renovando

  const geracaoDaRenovacao = geracao

  renovando = http
    .post('/auth/refresh/')
    .then(({ data }) => {
      definirAccessToken(data.access)
      aoRenovar(data.access)
      return data.access
    })
    .catch((falha) => {
      aoRenovar(null)
      // Falha de uma geração anterior (logout, troca de usuário) não derruba
      // quem acabou de entrar.
      if (avisarSeFalhar && geracaoDaRenovacao === geracao) {
        definirAccessToken(null)
        window.dispatchEvent(new CustomEvent('sessao-expirada'))
      }
      throw falha
    })
    .finally(() => {
      renovando = null
    })

  return renovando
}

// Qualquer escrita bem-sucedida pode ter cumprido uma missão do guia. Em vez de
// cada tela avisar o onboarding, o aviso sai daqui uma única vez.
const METODOS_DE_ESCRITA = new Set(['post', 'put', 'patch', 'delete'])
let avisoPendente

function avisarMudanca(config) {
  if (!METODOS_DE_ESCRITA.has((config?.method ?? '').toLowerCase())) return
  if (config?.url?.includes('/onboarding/')) return

  clearTimeout(avisoPendente)
  avisoPendente = setTimeout(
    () => window.dispatchEvent(new CustomEvent('dados-alterados')),
    300,
  )
}

http.interceptors.response.use(
  (resposta) => {
    avisarMudanca(resposta.config)
    return resposta
  },
  async (erro) => {
    const original = erro.config
    const ehLogin = original?.url?.includes('/auth/login')
    const ehRefresh = original?.url?.includes('/auth/refresh')

    if (erro.response?.status !== 401 || original._repetida || ehLogin || ehRefresh) {
      throw erro
    }

    // Resposta de uma sessão que já não existe: não renova nem avisa ninguém.
    if (original._geracao !== geracao) throw erro

    original._repetida = true

    const renovacao = renovarSessao({ avisarSeFalhar: true })

    const espera = new Promise((resolver) => fila.push(resolver))
    await renovacao.catch(() => undefined)
    const token = await espera

    if (!token) throw erro
    original.headers.Authorization = `Bearer ${token}`
    return http(original)
  },
)

export default http
