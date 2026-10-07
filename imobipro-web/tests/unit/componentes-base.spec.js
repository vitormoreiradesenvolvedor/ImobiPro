import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import ConfirmHost from '@/components/base/ConfirmHost.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import ToastHost from '@/components/base/ToastHost.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'

describe('BaseButton', () => {
  it('nasce como type=button para não submeter formulário sem querer', () => {
    const tela = mount(BaseButton, { slots: { default: 'Salvar' } })

    expect(tela.find('button').attributes('type')).toBe('button')
    expect(tela.text()).toContain('Salvar')
  })

  it('bloqueia clique enquanto carrega', () => {
    const tela = mount(BaseButton, { props: { carregando: true } })

    expect(tela.find('button').element.disabled).toBe(true)
    expect(tela.find('svg').exists()).toBe(true)
  })

  it('aplica a variante de perigo', () => {
    const tela = mount(BaseButton, { props: { variante: 'perigo' } })

    expect(tela.find('button').classes().join(' ')).toContain('bg-red-600')
  })
})

describe('BaseInput', () => {
  it('associa o rótulo ao campo pelo id', () => {
    const tela = mount(BaseInput, { props: { rotulo: 'E-mail' } })

    const id = tela.find('input').attributes('id')
    expect(tela.find('label').attributes('for')).toBe(id)
  })

  it('marca aria-invalid e mostra a mensagem quando há erro', () => {
    const tela = mount(BaseInput, { props: { rotulo: 'CPF', erro: 'CPF inválido.' } })

    expect(tela.find('input').attributes('aria-invalid')).toBe('true')
    expect(tela.text()).toContain('CPF inválido.')
  })

  it('propaga o valor digitado', async () => {
    const tela = mount(BaseInput, { props: { rotulo: 'Nome', modelValue: '' } })

    await tela.find('input').setValue('Ana')

    expect(tela.emitted('update:modelValue')[0]).toEqual(['Ana'])
  })
})

describe('BaseSelect', () => {
  it('aceita lista de strings e de objetos', () => {
    const strings = mount(BaseSelect, { props: { opcoes: ['A', 'B'] } })
    const objetos = mount(BaseSelect, {
      props: { opcoes: [{ value: '1', label: 'Um' }], placeholder: 'Selecione' },
    })

    expect(strings.findAll('option')).toHaveLength(2)
    expect(objetos.text()).toContain('Um')
    expect(objetos.text()).toContain('Selecione')
  })
})

describe('MoneyInput', () => {
  it('mostra máscara em real mas guarda número puro', async () => {
    const tela = mount(MoneyInput, { props: { modelValue: '2500.00' } })
    expect(tela.find('input').element.value).toContain('2.500,00')

    await tela.find('input').setValue('189900')

    expect(tela.emitted('update:modelValue').at(-1)).toEqual(['1899.00'])
  })

  it('limpar o campo devolve valor vazio, não zero', async () => {
    const tela = mount(MoneyInput, { props: { modelValue: '150.00' } })

    await tela.find('input').setValue('')

    expect(tela.emitted('update:modelValue').at(-1)).toEqual([''])
  })
})

describe('StatusBadge', () => {
  it('usa verde para estado positivo e vermelho para negativo', () => {
    const pago = mount(StatusBadge, { props: { status: 'PAGA', rotulo: 'Paga' } })
    const atrasado = mount(StatusBadge, { props: { status: 'ATRASADA' } })

    expect(pago.classes().join(' ')).toContain('emerald')
    expect(atrasado.classes().join(' ')).toContain('red')
  })

  it('cai no cinza para status desconhecido', () => {
    const tela = mount(StatusBadge, { props: { status: 'ESTADO_NOVO' } })

    expect(tela.classes().join(' ')).toContain('slate')
  })
})

describe('BaseTable', () => {
  const colunas = [
    { campo: 'nome', rotulo: 'Nome' },
    { campo: 'valor', rotulo: 'Valor', alinhamento: 'direita' },
  ]

  it('renderiza cabeçalho e linhas', () => {
    const tela = mount(BaseTable, {
      props: { colunas, linhas: [{ id: 1, nome: 'Ana', valor: 10 }] },
    })

    expect(tela.text()).toContain('Nome')
    expect(tela.text()).toContain('Ana')
  })

  it('emite a linha selecionada no clique', async () => {
    const linha = { id: 1, nome: 'Ana', valor: 10 }
    const tela = mount(BaseTable, { props: { colunas, linhas: [linha] } })

    await tela.find('tbody tr').trigger('click')

    expect(tela.emitted('selecionar')[0]).toEqual([linha])
  })

  it('mostra estado de carregamento no lugar das linhas', () => {
    const tela = mount(BaseTable, { props: { colunas, linhas: [], carregando: true } })

    expect(tela.text()).toContain('Carregando')
  })
})

describe('PaginacaoSimples', () => {
  it('some quando só existe uma página', () => {
    const tela = mount(PaginacaoSimples, {
      props: { pagina: 1, totalPaginas: 1, total: 5 },
    })

    expect(tela.find('nav').exists()).toBe(false)
  })

  it('desabilita "Anterior" na primeira página e avança na próxima', async () => {
    const tela = mount(PaginacaoSimples, {
      props: { pagina: 1, totalPaginas: 3, total: 60 },
    })

    const [anterior, proxima] = tela.findAll('button')
    expect(anterior.element.disabled).toBe(true)

    await proxima.trigger('click')
    expect(tela.emitted('update:pagina')[0]).toEqual([2])
  })
})

describe('BaseModal', () => {
  it('usa <dialog> nativo e fecha no Esc', async () => {
    const tela = mount(BaseModal, { props: { titulo: 'Confirmar' }, attachTo: document.body })

    expect(tela.find('dialog').exists()).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await tela.vm.$nextTick()

    expect(tela.emitted('fechar')).toBeTruthy()
    tela.unmount()
  })

  it('fecha ao clicar no fundo', async () => {
    const tela = mount(BaseModal, { props: { titulo: 'Confirmar' } })

    await tela.find('.fixed.inset-0.bg-slate-900\\/50').trigger('click')

    expect(tela.emitted('fechar')).toBeTruthy()
  })
})

describe('DataEmptyState e BaseCard', () => {
  it('estado vazio traz título, descrição e espaço para ação', () => {
    const tela = mount(DataEmptyState, {
      props: { titulo: 'Sem imóveis', descricao: 'Cadastre o primeiro.' },
      slots: { acao: '<button type="button">Cadastrar</button>' },
    })

    expect(tela.text()).toContain('Sem imóveis')
    expect(tela.text()).toContain('Cadastre o primeiro.')
    expect(tela.find('button').exists()).toBe(true)
  })

  it('card mostra título, subtítulo e conteúdo', () => {
    const tela = mount(BaseCard, {
      props: { titulo: 'Valores', subtitulo: 'do contrato' },
      slots: { default: '<p>R$ 100</p>' },
    })

    expect(tela.text()).toContain('Valores')
    expect(tela.text()).toContain('do contrato')
    expect(tela.text()).toContain('R$ 100')
  })

  it('textarea propaga o texto digitado', async () => {
    const tela = mount(BaseTextarea, { props: { rotulo: 'Observação' } })

    await tela.find('textarea').setValue('tudo certo')

    expect(tela.emitted('update:modelValue')[0]).toEqual(['tudo certo'])
  })
})

describe('ToastHost', () => {
  it('exibe e remove avisos', async () => {
    vi.useFakeTimers()
    const { sucesso } = useToast()
    const tela = mount(ToastHost)

    sucesso('Salvo com sucesso.')
    await tela.vm.$nextTick()
    expect(tela.text()).toContain('Salvo com sucesso.')

    await tela.find('button').trigger('click')
    expect(tela.text()).not.toContain('Salvo com sucesso.')
    vi.useRealTimers()
  })
})

describe('ConfirmHost', () => {
  it('resolve true ao confirmar', async () => {
    const { confirmar } = useConfirmacao()
    const tela = mount(ConfirmHost)

    const promessa = confirmar({ titulo: 'Remover?', mensagem: 'Some do anúncio.' })
    await tela.vm.$nextTick()
    expect(tela.text()).toContain('Some do anúncio.')

    const botoes = tela.findAll('button')
    await botoes[botoes.length - 1].trigger('click')

    await expect(promessa).resolves.toBe(true)
  })

  it('resolve null quando o diálogo de texto é cancelado', async () => {
    const { perguntar } = useConfirmacao()
    const tela = mount(ConfirmHost)

    const promessa = perguntar({ titulo: 'Motivo', rotulo: 'Motivo' })
    await tela.vm.$nextTick()

    const cancelar = tela.findAll('button').find((b) => b.text() === 'Cancelar')
    await cancelar.trigger('click')

    await expect(promessa).resolves.toBeNull()
  })
})
