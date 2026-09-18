import { readonly, ref } from 'vue'

const avisos = ref([])
let sequencia = 0

function adicionar(mensagem, tipo = 'info', duracao = 4500) {
  const id = ++sequencia
  avisos.value.push({ id, mensagem, tipo })
  setTimeout(() => remover(id), duracao)
  return id
}

function remover(id) {
  avisos.value = avisos.value.filter((aviso) => aviso.id !== id)
}

/** Extrai a mensagem útil do erro da API nunca mostra "[object Object]". */
function mensagemDoErro(erro, alternativa = 'Não foi possível concluir a operação.') {
  const dados = erro?.response?.data
  if (!dados) return alternativa
  if (dados.detail && dados.code !== 'validacao') return dados.detail

  const primeiro = primeiraMensagem(dados.campos ?? {})
  return primeiro ?? dados.detail ?? alternativa
}

/** Percorre erros aninhados do DRF e devolve a primeira mensagem legível. */
function primeiraMensagem(campos, prefixo = '') {
  for (const [campo, valor] of Object.entries(campos)) {
    const nome = prefixo ? `${prefixo} › ${campo}` : campo
    if (Array.isArray(valor) && valor.length) return `${nome}: ${valor[0]}`
    if (typeof valor === 'string') return `${nome}: ${valor}`
    if (valor && typeof valor === 'object') {
      const aninhada = primeiraMensagem(valor, nome)
      if (aninhada) return aninhada
    }
  }
  return null
}

export function useToast() {
  return {
    avisos: readonly(avisos),
    sucesso: (mensagem) => adicionar(mensagem, 'sucesso'),
    erro: (mensagem) => adicionar(mensagem, 'erro', 6000),
    info: (mensagem) => adicionar(mensagem, 'info'),
    erroDaApi: (erro, alternativa) =>
      adicionar(mensagemDoErro(erro, alternativa), 'erro', 6000),
    remover,
    mensagemDoErro,
  }
}
