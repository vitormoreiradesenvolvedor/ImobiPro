import { ref, shallowRef } from 'vue'

/**
 * Confirmação e entrada de texto sem `window.confirm`/`window.prompt`.
 *
 * Os diálogos nativos travam a thread do navegador, não são estilizáveis e
 * não passam em auditoria de acessibilidade. Aqui a promessa resolve quando o
 * usuário decide, e o host renderiza um modal de verdade.
 */
const pedido = shallowRef(null)
const aberto = ref(false)
let resolver = null

function abrir(configuracao) {
  pedido.value = configuracao
  aberto.value = true
  return new Promise((resolve) => {
    resolver = resolve
  })
}

function responder(valor) {
  aberto.value = false
  pedido.value = null
  resolver?.(valor)
  resolver = null
}

export function useConfirmacao() {
  return {
    pedido,
    aberto,
    responder,

    /** Devolve true/false. */
    confirmar: ({ titulo, mensagem, confirmar = 'Confirmar', perigo = false }) =>
      abrir({ tipo: 'confirmacao', titulo, mensagem, confirmar, perigo }),

    /** Devolve o texto digitado ou null se o usuário cancelar. */
    perguntar: ({ titulo, mensagem = '', rotulo = '', valorInicial = '' }) =>
      abrir({ tipo: 'texto', titulo, mensagem, rotulo, valorInicial }),
  }
}
