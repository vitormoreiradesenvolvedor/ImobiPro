import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authService } from '@/services/auth.service'
import { definirAccessToken, renovarSessao } from '@/services/http'

// Marcador (não é credencial) de que existe um refresh token no cookie
// HttpOnly. Sem ele, a SPA não dispara refresh em visita anônima o que
// evitava um 401 inútil a cada carregamento da tela de login.
const CHAVE_SESSAO = 'imobipro:sessao'

/**
 * localStorage pode não existir (navegação privada no Safari, iframe com
 * cookies bloqueados, ambiente de teste). O marcador é só uma otimização, então
 * a falha aqui nunca pode derrubar a autenticação.
 */
const marcador = {
  gravar() {
    try {
      window.localStorage?.setItem(CHAVE_SESSAO, '1')
    } catch {
      /* sem armazenamento: seguimos tentando o refresh no próximo boot */
    }
  },
  existe() {
    try {
      // Sem armazenamento disponível, assume que pode haver sessão: melhor um
      // refresh a mais do que deslogar quem estava autenticado.
      if (!window.localStorage) return true
      return Boolean(window.localStorage.getItem(CHAVE_SESSAO))
    } catch {
      return true
    }
  },
  apagar() {
    try {
      window.localStorage?.removeItem(CHAVE_SESSAO)
    } catch {
      /* nada a fazer */
    }
  },
}

export const useAuthStore = defineStore('auth', () => {
  const usuario = ref(null)
  const tenant = ref(null)
  const permissoes = ref({})
  const carregando = ref(false)
  const erro = ref(null)
  const errosCampos = ref({})

  const autenticado = computed(() => usuario.value !== null)
  const papel = computed(() => usuario.value?.papel ?? null)

  function aplicarPerfil(dados) {
    usuario.value = dados
    tenant.value = dados.tenant
    permissoes.value = dados.permissoes ?? {}

    // Identidade visual do tenant vira variável CSS consumida pelo Tailwind.
    if (dados.tenant?.cor_primaria) {
      document.documentElement.style.setProperty('--cor-primaria', dados.tenant.cor_primaria)
    }
  }

  function limpar() {
    usuario.value = null
    tenant.value = null
    permissoes.value = {}
    definirAccessToken(null)
    marcador.apagar()
  }

  async function login(email, senha) {
    carregando.value = true
    erro.value = null
    try {
      const { data } = await authService.login(email, senha)
      definirAccessToken(data.access)
      aplicarPerfil(data.user)
      marcador.gravar()
      return true
    } catch (falha) {
      erro.value = falha.response?.data?.detail ?? 'Não foi possível entrar. Tente novamente.'
      return false
    } finally {
      carregando.value = false
    }
  }

  /**
   * Cadastre-se: a API cria imobiliária e administrador e já devolve a sessão
   * no mesmo formato do login. Erros de campo voltam em `errosCampos` para a
   * tela marcar cada input.
   */
  async function cadastrar(dados) {
    carregando.value = true
    erro.value = null
    errosCampos.value = {}
    try {
      const { data } = await authService.cadastrar(dados)
      definirAccessToken(data.access)
      aplicarPerfil(data.user)
      marcador.gravar()
      return true
    } catch (falha) {
      const corpo = falha.response?.data
      errosCampos.value = corpo?.campos ?? {}
      erro.value = corpo?.detail ?? 'Não foi possível concluir o cadastro. Tente novamente.'
      return false
    } finally {
      carregando.value = false
    }
  }

  /**
   * Recupera a sessão no boot da SPA usando o cookie HttpOnly de refresh.
   *
   * Sempre com uma segunda tentativa, por dois motivos diferentes:
   *
   * - o refresh token gira a cada uso, então recarregar a página no exato
   *   instante de uma renovação em voo manda o cookie antigo e leva 401,
   *   embora a sessão esteja perfeitamente viva;
   * - excesso de requisições, erro do servidor ou rede instável não podem
   *   deslogar quem estava dentro.
   *
   * Só descarta a sessão quando a segunda tentativa também diz que ela não vale
   * (401 ou 403). Falha passageira preserva o marcador para a próxima carga.
   */
  async function restaurarSessao() {
    if (!marcador.existe()) return

    const sessaoInvalida = (falha) => [401, 403].includes(falha?.response?.status)

    for (const tentativa of [0, 1]) {
      try {
        // Passa pela renovação compartilhada: se o interceptador já estiver
        // renovando, o boot aproveita a mesma chamada em vez de disputar o
        // token com ela.
        await renovarSessao()
        const perfil = await authService.perfil()
        aplicarPerfil(perfil.data)
        return
      } catch (falha) {
        if (tentativa === 1) {
          if (sessaoInvalida(falha)) limpar()
          return
        }
        await new Promise((resolver) => setTimeout(resolver, 400))
      }
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } finally {
      limpar()
    }
  }

  function pode(permissao) {
    return Boolean(permissoes.value[permissao])
  }

  return {
    usuario,
    tenant,
    permissoes,
    carregando,
    erro,
    errosCampos,
    autenticado,
    papel,
    login,
    cadastrar,
    logout,
    restaurarSessao,
    limpar,
    pode,
  }
})
