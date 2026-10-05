import { readonly, ref } from 'vue'

/**
 * Tema claro e escuro da interface.
 *
 * A troca acontece em um atributo no `<html>`: o `style.css` redefine ali os
 * tokens de cor que o Tailwind já consome, então nenhuma tela precisa de
 * variante própria.
 *
 * A escolha do usuário manda e fica guardada. Sem escolha, vale a preferência
 * do sistema operacional, que é o comportamento que as pessoas esperam.
 */
const CHAVE = 'imobipro-tema'
const CLARO = 'claro'
const ESCURO = 'escuro'

const tema = ref(CLARO)

function guardado() {
  try {
    const valor = localStorage.getItem(CHAVE)
    return valor === CLARO || valor === ESCURO ? valor : null
  } catch {
    // Navegação anônima com armazenamento bloqueado não pode derrubar a tela.
    return null
  }
}

function preferenciaDoSistema() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? ESCURO : CLARO
}

export function aplicarTema(valor) {
  tema.value = valor
  document.documentElement.dataset.tema = valor
  try {
    localStorage.setItem(CHAVE, valor)
  } catch {
    // Sem persistência o tema vale só para esta aba, o que ainda é útil.
  }
}

export function iniciarTema() {
  const escolhido = guardado() ?? preferenciaDoSistema()
  tema.value = escolhido
  document.documentElement.dataset.tema = escolhido
  return escolhido
}

export function useTema() {
  if (!document.documentElement.dataset.tema) iniciarTema()
  else tema.value = document.documentElement.dataset.tema

  return {
    tema: readonly(tema),
    escuro: () => tema.value === ESCURO,
    alternar: () => aplicarTema(tema.value === ESCURO ? CLARO : ESCURO),
  }
}
