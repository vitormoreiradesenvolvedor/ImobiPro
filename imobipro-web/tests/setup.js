/**
 * Preparação comum da suíte unitária.
 *
 * Este jsdom não expõe `window.localStorage`. Como a aplicação usa o
 * armazenamento apenas como marcador de sessão (e trata sua ausência), aqui
 * instalamos uma implementação em memória para que os testes exercitem o
 * caminho normal a ausência é coberta pela blindagem da própria store.
 */
if (!window.localStorage) {
  const memoria = new Map()

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (chave) => (memoria.has(chave) ? memoria.get(chave) : null),
      setItem: (chave, valor) => memoria.set(chave, String(valor)),
      removeItem: (chave) => memoria.delete(chave),
      clear: () => memoria.clear(),
      key: (indice) => [...memoria.keys()][indice] ?? null,
      get length() {
        return memoria.size
      },
    },
  })
}
