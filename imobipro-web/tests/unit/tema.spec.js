import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AlternadorTema from '@/components/base/AlternadorTema.vue'
import { aplicarTema, iniciarTema, useTema } from '@/composables/useTema'

function sistemaPrefere(escuro) {
  window.matchMedia = vi.fn().mockReturnValue({ matches: escuro, addEventListener: vi.fn() })
}

describe('tema claro e escuro', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.tema
    sistemaPrefere(false)
  })

  it('sem escolha guardada, segue a preferência do sistema', () => {
    sistemaPrefere(true)

    expect(iniciarTema()).toBe('escuro')
    expect(document.documentElement.dataset.tema).toBe('escuro')
  })

  it('a escolha do usuário vence a preferência do sistema', () => {
    sistemaPrefere(true)
    aplicarTema('claro')

    delete document.documentElement.dataset.tema
    expect(iniciarTema()).toBe('claro')
  })

  it('alternar troca o atributo do documento e persiste', () => {
    iniciarTema()
    const { alternar, tema } = useTema()

    alternar()

    expect(tema.value).toBe('escuro')
    expect(document.documentElement.dataset.tema).toBe('escuro')
    expect(localStorage.getItem('imobipro-tema')).toBe('escuro')

    alternar()

    expect(document.documentElement.dataset.tema).toBe('claro')
  })

  it('armazenamento bloqueado não derruba a tela', () => {
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = () => {
      throw new Error('bloqueado')
    }

    expect(() => aplicarTema('escuro')).not.toThrow()
    expect(document.documentElement.dataset.tema).toBe('escuro')

    Storage.prototype.setItem = original
  })

  it('o botão anuncia o próximo tema e o estado atual', async () => {
    iniciarTema()
    const tela = mount(AlternadorTema)

    expect(tela.get('button').attributes('aria-label')).toBe('Usar tema escuro')
    expect(tela.get('button').attributes('aria-pressed')).toBe('false')

    await tela.get('button').trigger('click')

    expect(tela.get('button').attributes('aria-label')).toBe('Usar tema claro')
    expect(tela.get('button').attributes('aria-pressed')).toBe('true')
  })
})
