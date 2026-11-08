import { useState } from 'react'
import {
  ArrowRightLeftIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  LayoutGridIcon,
  ListIcon,
  LockIcon,
} from 'lucide-react'
import {
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from '@tanstack/react-query'

import { CardThumb } from '@/components/cards/card-thumb'
import { CardTitle } from '@/components/cards/card-title'
import {
  ColorIdentity,
  colorNames,
  colorSymbolUrl,
} from '@/components/cards/color-identity'
import { ManaCost } from '@/components/cards/mana-cost'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { CopyDetailDialog } from '@/components/copies/copy-detail-dialog'
import { CopyMark, CopyMarkBadge } from '@/components/copies/copy-mark'
import { RegisterCopyDialog } from '@/components/copies/register-copy-dialog'
import { SelectDeckDialog } from '@/components/decks/select-deck-dialog'
import type { DeckMode } from '@/components/decks/select-deck-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { ActionMenu } from '@/components/ui/action-menu'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { meQueryOptions } from '@/lib/api/auth'
import {
  copiesQueryOptions,
  deleteCopy,
  filterCopies,
  refreshCopyPrice,
  shareCopy,
  unlinkCopy,
} from '@/lib/api/copies'
import type {
  BulkEstado,
  BulkSearch,
  BulkView,
  ColorCode,
  Copy,
  ManaBucket,
} from '@/lib/api/copies'
import { decksQueryOptions } from '@/lib/api/decks'
import { groupsQueryOptions } from '@/lib/api/groups'
import { personName } from '@/lib/api/schemas'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import { cancelRequest } from '@/lib/api/requests'
import {
  bulkPrimary,
  bulkPrimaryLabel,
  copyActionLabel,
  copyStateText,
  planBulkMenu,
} from '@/lib/copy-actions'
import type { CopyAction } from '@/lib/copy-actions'
import { groupCopies, summarizeStates } from '@/lib/copy-groups'
import { isLegendary } from '@/lib/display'
import { formatCopyPrice } from '@/lib/money'
import { cn } from '@/lib/utils'

const visibilityOptions: Array<{ value: BulkEstado | ''; label: string }> = [
  { value: '', label: 'Livre' },
  { value: 'todas', label: 'Todas' },
  { value: 'in_deck', label: 'Reservadas' },
]

const colorCodes: Array<ColorCode> = ['W', 'U', 'B', 'R', 'G', 'C']

const VIEW_PREFERENCE_KEY = 'magic-bulk.bulk-view'

function useBulkView() {
  const [view, setView] = useState<BulkView>(() => {
    if (typeof localStorage === 'undefined') {
      return 'cartas'
    }

    return localStorage.getItem(VIEW_PREFERENCE_KEY) === 'lista'
      ? 'lista'
      : 'cartas'
  })

  function changeView(next: BulkView) {
    setView(next)

    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(VIEW_PREFERENCE_KEY, next)
    }
  }

  return [view, changeView] as const
}

const manaOptions: Array<{ value: ManaBucket | ''; label: string }> = [
  { value: '', label: 'Custo de mana' },
  { value: '0', label: 'Custo 0' },
  { value: '1', label: 'Custo 1' },
  { value: '2', label: 'Custo 2' },
  { value: '3', label: 'Custo 3' },
  { value: '4', label: 'Custo 4' },
  { value: '5', label: 'Custo 5' },
  { value: '6', label: 'Custo 6' },
  { value: '7+', label: 'Custo 7+' },
]

type PendingDeck = {
  copy: Copy
  mode: DeckMode
  fromDeckId?: string
}

export function BulkPage({
  groupId,
  search,
  onSearchChange,
}: {
  groupId: string
  search: BulkSearch
  onSearchChange: (search: BulkSearch) => void
}) {
  const queryClient = useQueryClient()
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const { data: copies } = useSuspenseQuery(copiesQueryOptions(groupId))
  const { data: decks } = useSuspenseQuery(decksQueryOptions())
  const visible = filterCopies(copies, search)
  const [view, changeView] = useBulkView()
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [registerOpen, setRegisterOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<Copy | null>(null)
  const [cancelTarget, setCancelTarget] = useState<Copy | null>(null)
  const [pendingDeck, setPendingDeck] = useState<PendingDeck | null>(null)
  const [groupsTarget, setGroupsTarget] = useState<Copy | null>(null)
  const [detail, setDetail] = useState<Copy | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function run(key: string, action: () => Promise<unknown>) {
    setBusy(key)
    try {
      await action()
      await invalidateBoard(queryClient)
    } catch (error) {
      await reportBoardError(queryClient, error)
    } finally {
      setBusy(null)
    }
  }

  function selectCopy(copy: Copy) {
    if (copy.visibility === 'in_deck' && copy.deck?.owner.id === me.id) {
      setPendingDeck({ copy, mode: 'move', fromDeckId: copy.deck.id })
      return
    }

    if (copy.holder.id === me.id) {
      setPendingDeck({ copy, mode: 'take' })
      return
    }

    setPendingDeck({ copy, mode: 'request' })
  }

  function perform(copy: Copy, action: CopyAction) {
    if (action === 'request') {
      setPendingDeck({ copy, mode: 'request' })
      return
    }

    if (action === 'groups') {
      setGroupsTarget(copy)
      return
    }

    if (action === 'remove') {
      setRemoveTarget(copy)
      return
    }

    if (action === 'cancel') {
      setCancelTarget(copy)
      return
    }

    if (action === 'refresh') {
      void run(`refresh:${copy.id}`, () => refreshCopyPrice(copy.id))
    }
  }

  function toggle(oracleId: string) {
    setExpanded((current) => {
      const next = new Set(current)

      if (next.has(oracleId)) {
        next.delete(oracleId)
      } else {
        next.add(oracleId)
      }

      return next
    })
  }

  const openCopy = detail
    ? (copies.find((copy) => copy.id === detail.id) ?? null)
    : null

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bulk"
        action={
          <Button
            type="button"
            onClick={() => {
              setRegisterOpen(true)
            }}
          >
            Cadastrar carta
          </Button>
        }
      />
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <form
            className="flex w-full min-w-0 flex-1 flex-col gap-2 sm:w-auto sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault()
              const formData = new FormData(event.currentTarget)
              const q = String(formData.get('q') ?? '').trim()
              onSearchChange({
                ...search,
                ...(q ? { q } : { q: undefined }),
              })
            }}
          >
            <Input
              name="q"
              defaultValue={search.q ?? ''}
              placeholder="Filtrar por nome"
              aria-label="Filtrar por nome"
            />
            <NativeSelect
              aria-label="Estado"
              className="sm:w-40"
              value={search.estado ?? ''}
              onChange={(event) => {
                const estado = event.target.value as BulkEstado | ''
                onSearchChange({
                  ...search,
                  estado: estado || undefined,
                })
              }}
            >
              {visibilityOptions.map((option) => (
                <option key={option.label} value={option.value}>
                  {option.label}
                </option>
              ))}
            </NativeSelect>
            <Button type="submit" variant="outline">
              Filtrar
            </Button>
          </form>
          <OrganizationToggle view={view} onChange={changeView} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ColorFilter
            selected={search.cores ?? []}
            onToggle={(color) => {
              const current = search.cores ?? []
              const cores = current.includes(color)
                ? current.filter((item) => item !== color)
                : [...current, color]
              onSearchChange({
                ...search,
                cores: cores.length > 0 ? cores : undefined,
              })
            }}
          />
          <NativeSelect
            aria-label="Custo de mana"
            className="w-40"
            value={search.cmc ?? ''}
            onChange={(event) => {
              const cmc = event.target.value as ManaBucket | ''
              onSearchChange({
                ...search,
                cmc: cmc || undefined,
              })
            }}
          >
            {manaOptions.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </NativeSelect>
          {search.q || search.estado || search.cores || search.cmc ? (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                onSearchChange({ destino: search.destino })
              }}
            >
              Limpar filtros
            </Button>
          ) : null}
        </div>
      </div>
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {copies.length === 0
            ? 'Nenhuma carta neste grupo.'
            : 'Nenhuma carta com esse filtro.'}
        </p>
      ) : view === 'lista' ? (
        <BulkList
          copies={visible}
          expanded={expanded}
          meId={me.id}
          busy={busy}
          onToggle={toggle}
          onPerform={perform}
          onInspect={setDetail}
          onPrimary={selectCopy}
        />
      ) : (
        <BulkGrid
          copies={visible}
          meId={me.id}
          busy={busy}
          onPerform={perform}
          onInspect={setDetail}
          onPrimary={selectCopy}
        />
      )}
      <RegisterCopyDialog
        open={registerOpen}
        onOpenChange={setRegisterOpen}
        groupId={groupId}
        meId={me.id}
      />
      <GroupsDialog
        copy={groupsTarget}
        groupId={groupId}
        onOpenChange={(open) => {
          if (!open) {
            setGroupsTarget(null)
          }
        }}
        onChanged={async (next) => {
          setGroupsTarget(next)
          await invalidateBoard(queryClient)
        }}
      />
      <CopyDetailDialog
        copy={openCopy}
        onOpenChange={(open) => {
          if (!open) {
            setDetail(null)
          }
        }}
        actions={
          openCopy ? (
            <CopyActionButtons
              copy={openCopy}
              meId={me.id}
              busy={busy}
              buttonClassName="w-40 max-w-full"
              onPerform={perform}
              onPrimary={selectCopy}
            />
          ) : null
        }
      />
      <ConfirmDialog
        open={removeTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setRemoveTarget(null)
          }
        }}
        title="Remover carta"
        description="Isso apaga o registro em todos os grupos. Só faça isso se o papel saiu de circulação."
        confirmLabel="Remover"
        destructive
        pending={busy != null}
        onConfirm={() => {
          if (!removeTarget) {
            return
          }

          const copyId = removeTarget.id
          setRemoveTarget(null)
          void run(`remove:${copyId}`, () => deleteCopy(copyId))
        }}
      />
      <ConfirmDialog
        open={cancelTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setCancelTarget(null)
          }
        }}
        title="Cancelar pedido"
        description="O pedido é desfeito e a carta volta para onde estava."
        confirmLabel="Cancelar pedido"
        destructive
        pending={busy != null}
        onConfirm={() => {
          if (!cancelTarget?.open_request) {
            return
          }

          const requestId = cancelTarget.open_request.id
          const copyId = cancelTarget.id
          setCancelTarget(null)
          void run(`cancel:${copyId}`, () => cancelRequest(requestId))
        }}
      />
      <SelectDeckDialog
        open={pendingDeck != null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeck(null)
          }
        }}
        copy={pendingDeck?.copy ?? null}
        mode={pendingDeck?.mode ?? 'take'}
        fromDeckId={pendingDeck?.fromDeckId}
        groupId={groupId}
        decks={
          pendingDeck?.mode === 'move' && pendingDeck.fromDeckId
            ? decks.filter((deck) => deck.id !== pendingDeck.fromDeckId)
            : decks
        }
        preferredDeckId={search.destino}
        onDone={async () => {
          setPendingDeck(null)
          await invalidateBoard(queryClient)
        }}
      />
    </div>
  )
}

function ColorFilter({
  selected,
  onToggle,
}: {
  selected: Array<ColorCode>
  onToggle: (color: ColorCode) => void
}) {
  return (
    <div
      role="group"
      aria-label="Filtrar por cor"
      className="flex flex-wrap items-center gap-1"
    >
      {colorCodes.map((color) => {
        const active = selected.includes(color)

        return (
          <button
            key={color}
            type="button"
            aria-pressed={active}
            title={colorNames[color]}
            onClick={() => {
              onToggle(color)
            }}
            className={cn(
              'size-8 shrink-0 overflow-hidden rounded-full p-0 outline-none transition-all duration-150 focus-visible:scale-105 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring/50',
              active
                ? 'scale-110 opacity-100'
                : 'opacity-50 hover:scale-105 hover:opacity-80',
            )}
          >
            <img
              src={colorSymbolUrl(color)}
              alt={colorNames[color]}
              className="block size-full rounded-full"
            />
          </button>
        )
      })}
    </div>
  )
}

function OrganizationToggle({
  view,
  onChange,
}: {
  view: BulkView
  onChange: (view: BulkView) => void
}) {
  const options = [
    { id: 'cartas' as const, label: 'Cartas', icon: LayoutGridIcon },
    { id: 'lista' as const, label: 'Lista', icon: ListIcon },
  ]

  return (
    <div
      role="group"
      aria-label="Organização"
      className="flex shrink-0 self-end sm:self-auto"
    >
      {options.map((option) => {
        const Icon = option.icon
        const selected = view === option.id

        return (
          <Button
            key={option.id}
            type="button"
            variant="outline"
            aria-pressed={selected}
            className={cn(
              option.id === 'cartas'
                ? 'rounded-r-none'
                : '-ml-px rounded-l-none',
              selected && 'bg-muted',
            )}
            onClick={() => {
              onChange(option.id)
            }}
          >
            <Icon />
            {option.label}
          </Button>
        )
      })}
    </div>
  )
}

function CopyActionButtons({
  copy,
  meId,
  busy,
  onPerform,
  onPrimary,
  stretch = false,
  buttonClassName,
}: {
  copy: Copy
  meId: string
  busy: string | null
  onPerform: (copy: Copy, action: CopyAction) => void
  onPrimary: (copy: Copy) => void
  stretch?: boolean
  buttonClassName?: string
}) {
  const primary = bulkPrimary(copy, meId)
  const menu = planBulkMenu(copy, meId)
  const unavailable = primary === 'unavailable'

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-2',
        stretch ? 'w-full' : 'shrink-0 justify-end',
      )}
    >
      <Button
        type="button"
        variant={unavailable ? 'outline' : 'default'}
        className={
          stretch
            ? 'h-auto min-w-0 flex-1 whitespace-normal py-1'
            : buttonClassName
        }
        disabled={busy != null || unavailable}
        onClick={() => {
          if (primary === 'request') {
            onPerform(copy, 'request')
            return
          }

          onPrimary(copy)
        }}
      >
        {unavailable && copy.locked ? <LockIcon /> : null}
        {primary === 'request' ? <ArrowRightLeftIcon /> : null}
        {bulkPrimaryLabel(primary)}
      </Button>
      <ActionMenu
        items={menu.map((action) => ({
          id: action,
          label: copyActionLabel[action],
          destructive: action === 'remove',
          onSelect: () => {
            onPerform(copy, action)
          },
        }))}
      />
    </div>
  )
}

function CopyFacts({ copy }: { copy: Copy }) {
  const state = copyStateText(copy)

  return (
    <div className="flex min-w-48 flex-1 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <CopyMark copy={copy} />
      {state.detail ? (
        <span className="text-muted-foreground">{state.detail}</span>
      ) : null}
      <span className="text-muted-foreground">
        Casa {personName(copy.holder)}
      </span>
      <span className="text-muted-foreground">
        {formatCopyPrice(copy.price_cents, copy.catalog.is_basic)}
      </span>
    </div>
  )
}

function BulkList({
  copies,
  expanded,
  meId,
  busy,
  onToggle,
  onPerform,
  onPrimary,
  onInspect,
}: {
  copies: Array<Copy>
  expanded: Set<string>
  meId: string
  busy: string | null
  onToggle: (oracleId: string) => void
  onPerform: (copy: Copy, action: CopyAction) => void
  onPrimary: (copy: Copy) => void
  onInspect: (copy: Copy) => void
}) {
  const groups = groupCopies(copies)

  return (
    <ul className="flex flex-col gap-2">
      {groups.map((group) => {
        const single = group.copies.length === 1
        const open = single || expanded.has(group.oracleId)
        const only = single ? group.copies[0] : null

        return (
          <li
            key={group.oracleId}
            className="rounded-xl bg-card px-3 py-2 ring-1 ring-foreground/10"
          >
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              {only ? (
                <button
                  type="button"
                  className="shrink-0"
                  aria-label={`Ver ${group.catalog.name_pt ?? group.catalog.name_en}`}
                  onClick={() => {
                    onInspect(only)
                  }}
                >
                  <CardThumb url={group.catalog.image_url} preview={false} />
                </button>
              ) : (
                <CardThumb url={group.catalog.image_url} />
              )}
              <div className="flex min-w-0 flex-1 basis-52 flex-col gap-1">
                <div className="flex items-start gap-3">
                  <CardTitle
                    namePt={group.catalog.name_pt}
                    nameEn={group.catalog.name_en}
                  />
                  <ManaCost
                    cost={group.catalog.mana_cost}
                    className="shrink-0"
                  />
                </div>
                <ColorIdentity
                  colors={group.catalog.color_identity}
                  name={null}
                />
              </div>
              <p className="min-w-36 flex-1 text-sm text-muted-foreground">
                {group.catalog.type_line}
              </p>
              {only ? (
                <CopyFacts copy={only} />
              ) : (
                <p className="min-w-36 flex-1 text-sm">
                  {summarizeStates(group.copies)}
                </p>
              )}
              {only ? (
                <CopyActionButtons
                  copy={only}
                  meId={meId}
                  busy={busy}
                  onPerform={onPerform}
                  onPrimary={onPrimary}
                />
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  className="shrink-0"
                  aria-expanded={open}
                  aria-label={`${open ? 'Recolher' : 'Expandir'} ${group.copies.length} cópias`}
                  onClick={() => {
                    onToggle(group.oracleId)
                  }}
                >
                  ×{group.copies.length}
                  {open ? <ChevronDownIcon /> : <ChevronRightIcon />}
                </Button>
              )}
            </div>
            {!single && open ? (
              <ul className="mt-1 border-t border-foreground/10">
                {group.copies.map((copy) => (
                  <li
                    key={copy.id}
                    className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2"
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => {
                        onInspect(copy)
                      }}
                    >
                      <CopyFacts copy={copy} />
                    </button>
                    <CopyActionButtons
                      copy={copy}
                      meId={meId}
                      busy={busy}
                      onPerform={onPerform}
                      onPrimary={onPrimary}
                    />
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}

function BulkGrid({
  copies,
  meId,
  busy,
  onPerform,
  onPrimary,
  onInspect,
}: {
  copies: Array<Copy>
  meId: string
  busy: string | null
  onPerform: (copy: Copy, action: CopyAction) => void
  onPrimary: (copy: Copy) => void
  onInspect: (copy: Copy) => void
}) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7">
      {copies.map((copy) => {
        const name = copy.catalog.name_pt ?? copy.catalog.name_en
        const legendary = isLegendary(copy.catalog.type_line)
        const state = copyStateText(copy)
        const dimmed = copy.locked || copy.visibility === 'in_use_elsewhere'

        return (
          <li
            key={copy.id}
            className="relative flex h-full min-w-0 flex-col rounded-xl bg-card ring-1 ring-foreground/10"
          >
            <button
              type="button"
              className="absolute inset-0 rounded-xl"
              aria-label={`Ver ${name}`}
              onClick={() => {
                onInspect(copy)
              }}
            />
            <div
              className={cn(
                'pointer-events-none relative p-2 pb-0',
                dimmed && 'opacity-50',
              )}
            >
              <CardThumb
                url={copy.catalog.image_url}
                alt=""
                preview={false}
                className="aspect-[488/680] h-auto w-full rounded-[4.5%] object-cover"
              />
            </div>
            <CopyMarkBadge copy={copy} />
            <div
              className={cn(
                'pointer-events-none flex flex-1 flex-col gap-2 p-3 pt-2.5',
                dimmed && 'opacity-60',
              )}
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-heading text-base leading-snug">{name}</p>
                  <ManaCost
                    cost={copy.catalog.mana_cost}
                    className="shrink-0"
                  />
                </div>
                {copy.catalog.name_pt ? (
                  <p className="text-sm text-muted-foreground">
                    {copy.catalog.name_en}
                  </p>
                ) : null}
                <ColorIdentity
                  colors={copy.catalog.color_identity}
                  name={null}
                />
                {legendary ? (
                  <p className="text-sm text-amber-800 dark:text-amber-300">
                    Lendária
                  </p>
                ) : null}
              </div>
              <div className="mt-auto flex flex-col gap-2">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                  <CopyMark copy={copy} />
                  {state.detail ? (
                    <span className="text-muted-foreground">
                      {state.detail}
                    </span>
                  ) : null}
                </div>
                {copy.visibility === 'in_use_elsewhere' ? null : (
                  <p className="text-sm text-muted-foreground">
                    Casa {personName(copy.holder)}
                  </p>
                )}
              </div>
            </div>
            <div className="relative z-10 px-3 pb-3">
              <CopyActionButtons
                copy={copy}
                meId={meId}
                busy={busy}
                stretch
                onPerform={onPerform}
                onPrimary={onPrimary}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function GroupsDialog({
  copy,
  groupId,
  onOpenChange,
  onChanged,
}: {
  copy: Copy | null
  groupId: string
  onOpenChange: (open: boolean) => void
  onChanged: (next: Copy | null) => Promise<void>
}) {
  const { data: groups = [] } = useQuery({
    ...groupsQueryOptions(),
    enabled: copy != null,
  })
  const [pendingId, setPendingId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  return (
    <Dialog
      open={copy != null}
      onOpenChange={onOpenChange}
      title="Mudar bulks"
      description="Inclua a carta num grupo ou tire de um. Ela precisa continuar em pelo menos um. Para apagar de todos, use Remover."
    >
      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Você não está em um grupo.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {groups.map((group) => {
            const linked = copy?.group_ids.includes(group.id) ?? false

            return (
              <li
                key={group.id}
                className="flex items-center justify-between gap-3"
              >
                <span className="min-w-0 truncate text-sm">
                  {group.name}
                  {group.id === groupId ? ' · este bulk' : ''}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  disabled={
                    pendingId != null ||
                    !copy ||
                    (linked && copy.state !== 'available')
                  }
                  title={
                    linked && copy != null && copy.state !== 'available'
                      ? 'Devolva ao bulk antes de tirar o vínculo.'
                      : undefined
                  }
                  onClick={() => {
                    if (!copy) {
                      return
                    }

                    const copyId = copy.id
                    setPendingId(group.id)
                    const action = linked
                      ? unlinkCopy(copyId, group.id)
                      : shareCopy(copyId, group.id)

                    void action
                      .then(async (updated) => {
                        if (!updated.group_ids.includes(groupId)) {
                          await onChanged(null)
                          return
                        }

                        await onChanged(updated)
                      })
                      .catch((error: unknown) => {
                        reportBoardError(queryClient, error)
                      })
                      .finally(() => {
                        setPendingId(null)
                      })
                  }}
                >
                  {linked ? 'Tirar' : 'Incluir'}
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </Dialog>
  )
}
