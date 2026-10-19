const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export const moeda = (valor) => (valor == null ? '' : brl.format(Number(valor)))

export const data = (valor) =>
  valor ? new Intl.DateTimeFormat('pt-BR').format(new Date(valor)) : ''

export const dataHora = (valor) =>
  valor
    ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(
        new Date(valor),
      )
    : ''

export const cpfCnpj = (valor) => {
  const digitos = String(valor ?? '').replace(/\D/g, '')
  if (digitos.length === 11) {
    return digitos.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
  }
  if (digitos.length === 14) {
    return digitos.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
  }
  return valor ?? ''
}

export const telefone = (valor) => {
  const digitos = String(valor ?? '').replace(/\D/g, '')
  if (digitos.length === 11) return digitos.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3')
  if (digitos.length === 10) return digitos.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3')
  return valor ?? ''
}

export const iniciais = (nome) =>
  String(nome ?? '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')

/**
 * Converte número digitado em pt-BR para o formato que a API aceita.
 *
 * O usuário escreve "4,5"; DRF só entende "4.5". Vale para percentuais e outros
 * campos decimais digitados em texto livre dinheiro já passa pelo MoneyInput.
 */
export const decimalParaApi = (valor) =>
  typeof valor === 'string' ? valor.trim().replace(',', '.') : valor
