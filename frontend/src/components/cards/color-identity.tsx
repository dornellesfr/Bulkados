export const colorNames: Record<string, string> = {
  W: 'Branco',
  U: 'Azul',
  B: 'Preto',
  R: 'Vermelho',
  G: 'Verde',
  C: 'Incolor',
}

export function colorSymbolUrl(symbol: string) {
  return `https://svgs.scryfall.io/card-symbols/${symbol}.svg`
}

function symbolUrl(symbol: string) {
  return colorSymbolUrl(symbol)
}

export function ColorIdentity({
  colors,
  name,
}: {
  colors: Array<string> | null
  name: string | null
}) {
  if (colors === null) {
    return null
  }

  const symbols = colors.length === 0 ? ['C'] : colors

  return (
    <span className="inline-flex items-center gap-1.5 align-middle">
      {symbols.map((symbol) => (
        <img
          key={symbol}
          src={symbolUrl(symbol)}
          alt={colorNames[symbol] ?? symbol}
          title={colorNames[symbol] ?? symbol}
          className="size-4"
        />
      ))}
      {name ? <span>{name}</span> : null}
    </span>
  )
}
