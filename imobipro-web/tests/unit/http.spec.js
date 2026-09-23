import { beforeEach, describe, expect, it, vi } from 'vitest'

import http, { definirAccessToken } from '@/services/http'

/**
 * O cliente HTTP renova o token sozinho. O que se testa aqui é o caso chato:
 * uma resposta 401 que chega atrasada, depois de o usuário já ter saído e
 * entrado de novo ela não pode derrubar a sessão nova.
 */
describe('cliente HTTP', () => {
  beforeEach(() => {
    definirAccessToken(null)
    vi.restoreAllMocks()
  })

  function responder(mapa) {
    http.defaults.adapter = async (config) => {
      const resposta = mapa[config.url]
      if (typeof resposta === 'function') return resposta(config)
      throw Object.assign(new Error('401'), {
        config,
        response: { status: 401, data: {} },
      })
    }
  }

  it('não encerra a sessão quando o 401 é de uma sessão anterior', async () => {
    const avisou = vi.fn()
    window.addEventListener('sessao-expirada', avisou)

    definirAccessToken('token-antigo')
    responder({})

    let requisicaoSaiu
    const saiu = new Promise((resolver) => {
      requisicaoSaiu = resolver
    })
    const adaptadorOriginal = http.defaults.adapter
    http.defaults.adapter = (config) => {
      requisicaoSaiu()
      return adaptadorOriginal(config)
    }

    const pendente = http.get('/imoveis/').catch(() => 'falhou')
    await saiu
    // O usuário entra de novo enquanto a requisição antiga ainda está no ar.
    definirAccessToken('token-novo')

    await expect(pendente).resolves.toBe('falhou')
    expect(avisou).not.toHaveBeenCalled()

    window.removeEventListener('sessao-expirada', avisou)
  })

  it('avisa que a sessão expirou quando a renovação falha na sessão atual', async () => {
    const avisou = vi.fn()
    window.addEventListener('sessao-expirada', avisou)

    definirAccessToken('token-unico')
    responder({})

    await expect(http.get('/imoveis/')).rejects.toBeDefined()
    expect(avisou).toHaveBeenCalledTimes(1)

    window.removeEventListener('sessao-expirada', avisou)
  })
})
