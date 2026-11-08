import type { Copy } from '@/lib/api/copies'
import { copyStateText } from '@/lib/copy-actions'

export type CopyGroup = {
  oracleId: string
  catalog: Copy['catalog']
  copies: Array<Copy>
}

export function groupCopies(copies: Array<Copy>): Array<CopyGroup> {
  const groups = new Map<string, CopyGroup>()

  for (const copy of copies) {
    const group = groups.get(copy.catalog.oracle_id)

    if (group) {
      group.copies.push(copy)
    } else {
      groups.set(copy.catalog.oracle_id, {
        oracleId: copy.catalog.oracle_id,
        catalog: copy.catalog,
        copies: [copy],
      })
    }
  }

  return Array.from(groups.values())
}

export function summarizeStates(copies: Array<Copy>): string {
  const counts = new Map<string, number>()

  for (const copy of copies) {
    const label = copyStateText(copy).label
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }

  return Array.from(counts, ([label, count]) =>
    count > 1 ? `${label} ×${count}` : label,
  ).join(' · ')
}
