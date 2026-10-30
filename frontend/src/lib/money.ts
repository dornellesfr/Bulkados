const currency = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

export function formatCents(cents: number) {
  return currency.format(cents / 100)
}

export function formatCopyPrice(cents: number | null, isBasic: boolean) {
  if (isBasic) {
    return formatCents(0)
  }

  if (cents == null) {
    return 'sem preço'
  }

  return formatCents(cents)
}
