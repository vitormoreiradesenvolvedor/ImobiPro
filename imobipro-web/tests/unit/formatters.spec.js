import { describe, expect, it } from 'vitest'

import { cpfCnpj, decimalParaApi, iniciais, moeda, telefone } from '@/utils/formatters'

describe('formatadores', () => {
  it('formata moeda em real', () => {
    // O Intl separa o símbolo com espaço fino; a troca abaixo o normaliza.
    // eslint-disable-next-line no-irregular-whitespace
    expect(moeda(2500).replace(/ /g, ' ')).toBe('R$ 2.500,00')
  })

  it('mostra travessão quando não há valor', () => {
    expect(moeda(null)).toBe('')
  })

  it('formata CPF e CNPJ', () => {
    expect(cpfCnpj('12345678909')).toBe('123.456.789-09')
    expect(cpfCnpj('12345678000199')).toBe('12.345.678/0001-99')
  })

  it('formata telefone com e sem nono dígito', () => {
    expect(telefone('35998765432')).toBe('(35) 99876-5432')
    expect(telefone('3538765432')).toBe('(35) 3876-5432')
  })

  it('extrai as iniciais do nome', () => {
    expect(iniciais('Ana Ribeiro Costa')).toBe('AR')
  })

  it('troca a vírgula do usuário pelo ponto que a API exige', () => {
    expect(decimalParaApi('4,5')).toBe('4.5')
    expect(decimalParaApi(' 10,25 ')).toBe('10.25')
    expect(decimalParaApi('8')).toBe('8')
    expect(decimalParaApi(7.5)).toBe(7.5)
    expect(decimalParaApi(undefined)).toBeUndefined()
  })
})
