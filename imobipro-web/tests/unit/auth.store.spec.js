import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authService } from '@/services/auth.service'
import { renovarSessao } from '@/services/http'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/services/auth.service', () => ({
  authService: {
    login: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
    perfil: vi.fn(),
    solicitarResetSenha: vi.fn(),
  },
}))

// A renovação mora no cliente HTTP porque é lá que ela é serializada; o store
// só a consome.
vi.mock('@/services/http', () => ({
  default: { post: vi.fn(), get: vi.fn() },
  definirAccessToken: vi.fn(),
  renovarSessao: vi.fn(),
}))

const PERFIL = {
  id: 'uuid-1',
  email: 'admin@horizonteimoveis.com.br',
  nome_completo: 'Ana Ribeiro',
  papel: 'ADMIN',
  papel_display: 'Administrador da imobiliária',
  tenant: { id: 'uuid-t', nome_fantasia: 'Horizonte Imóveis', cor_primaria: '#123456' },
  permissoes: { ver_financeiro: true, ver_crm: true, gerenciar_usuarios: true },
}

describe('store de autenticação', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('guarda usuário, tenant e permissões após login', async () => {
    authService.login.mockResolvedValue({ data: { access: 'tok', user: PERFIL } })
    const auth = useAuthStore()

    expect(await auth.login('admin@horizonteimoveis.com.br', 'senha')).toBe(true)
    expect(auth.autenticado).toBe(true)
    expect(auth.tenant.nome_fantasia).toBe('Horizonte Imóveis')
    expect(auth.pode('ver_financeiro')).toBe(true)
  })

  it('aplica a cor do tenant na variável CSS', async () => {
    authService.login.mockResolvedValue({ data: { access: 'tok', user: PERFIL } })
    await useAuthStore().login('admin@horizonteimoveis.com.br', 'senha')

    expect(document.documentElement.style.getPropertyValue('--cor-primaria')).toBe('#123456')
  })

  it('expõe a mensagem de erro da API quando o login falha', async () => {
    authService.login.mockRejectedValue({
      response: { data: { detail: 'Credenciais inválidas.' } },
    })
    const auth = useAuthStore()

    expect(await auth.login('x@y.z', 'errada')).toBe(false)
    expect(auth.autenticado).toBe(false)
    expect(auth.erro).toBe('Credenciais inválidas.')
  })

  it('restaura a sessão pelo cookie de refresh', async () => {
    window.localStorage.setItem('imobipro:sessao', '1')
    renovarSessao.mockResolvedValue('tok')
    authService.perfil.mockResolvedValue({ data: PERFIL })
    const auth = useAuthStore()

    await auth.restaurarSessao()

    expect(auth.autenticado).toBe(true)
    expect(auth.usuario.email).toBe('admin@horizonteimoveis.com.br')
  })

  it('mantém o usuário deslogado quando a sessão não vale mais', async () => {
    window.localStorage.setItem('imobipro:sessao', '1')
    renovarSessao.mockRejectedValue({ response: { status: 401 } })
    const auth = useAuthStore()

    await auth.restaurarSessao()

    expect(renovarSessao).toHaveBeenCalledTimes(2)
    expect(auth.autenticado).toBe(false)
    expect(window.localStorage.getItem('imobipro:sessao')).toBeNull()
  })

  it('sobrevive ao 401 de um refresh que estava em voo na hora do F5', async () => {
    // O token gira a cada uso: recarregar durante uma renovação manda o cookie
    // antigo. A segunda tentativa já usa o novo e a sessão continua de pé.
    window.localStorage.setItem('imobipro:sessao', '1')
    renovarSessao
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce('tok')
    authService.perfil.mockResolvedValue({ data: PERFIL })
    const auth = useAuthStore()

    await auth.restaurarSessao()

    expect(auth.autenticado).toBe(true)
  })

  it('tenta de novo quando a falha é passageira, sem descartar a sessão', async () => {
    // Excesso de requisições ou servidor fora do ar não podem deslogar ninguém.
    window.localStorage.setItem('imobipro:sessao', '1')
    renovarSessao
      .mockRejectedValueOnce({ response: { status: 429 } })
      .mockResolvedValueOnce('tok')
    authService.perfil.mockResolvedValue({ data: PERFIL })
    const auth = useAuthStore()

    await auth.restaurarSessao()

    expect(renovarSessao).toHaveBeenCalledTimes(2)
    expect(auth.autenticado).toBe(true)
  })

  it('desiste sem apagar o marcador quando a falha passageira insiste', async () => {
    window.localStorage.setItem('imobipro:sessao', '1')
    renovarSessao.mockRejectedValue({ response: { status: 503 } })
    const auth = useAuthStore()

    await auth.restaurarSessao()

    expect(auth.autenticado).toBe(false)
    expect(window.localStorage.getItem('imobipro:sessao')).toBe('1')
  })

  it('limpa o estado no logout mesmo se a API falhar', async () => {
    authService.login.mockResolvedValue({ data: { access: 'tok', user: PERFIL } })
    authService.logout.mockRejectedValue(new Error('rede'))
    const auth = useAuthStore()
    await auth.login('admin@horizonteimoveis.com.br', 'senha')

    await expect(auth.logout()).rejects.toThrow()
    expect(auth.autenticado).toBe(false)
  })

  it('não chama refresh quando nunca houve login neste navegador', async () => {
    // Evita um 401 inútil a cada visita anônima à tela de login.
    window.localStorage.removeItem('imobipro:sessao')

    await useAuthStore().restaurarSessao()

    expect(renovarSessao).not.toHaveBeenCalled()
  })

  it('nega permissão desconhecida', () => {
    expect(useAuthStore().pode('exportar_tudo')).toBe(false)
  })
})
