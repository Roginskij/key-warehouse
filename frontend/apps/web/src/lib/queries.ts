import type { Schemas } from '@kv/api'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { useI18n } from 'vue-i18n'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

export type Item = Schemas['StockItemOut']
export type Location = Schemas['LocationOut']
export type MovementBody = Schemas['MovementIn']

const INV = '/api/v1/workshops/{workshop_id}/inventory' as const

export interface ItemFilters {
  q?: string
  kind?: string | null
  location_id?: string | null
  low_stock?: boolean
}

export function useItems(filters: MaybeRefOrGetter<ItemFilters>) {
  const s = useSession()
  return useQuery({
    queryKey: computed(() => ['items', s.wid, toValue(filters)]),
    queryFn: () => {
      const f = toValue(filters)
      return call(
        client.GET(`${INV}/items`, {
          params: {
            path: { workshop_id: s.wid },
            query: {
              q: f.q || undefined,
              kind: (f.kind as Schemas['ItemKind']) || undefined,
              location_id: f.location_id || undefined,
              low_stock: f.low_stock || undefined,
              limit: 500,
            },
          },
        }),
      )
    },
    enabled: computed(() => !!s.wid),
    placeholderData: keepPreviousData,
  })
}

export function useItem(id: MaybeRefOrGetter<string>) {
  const s = useSession()
  return useQuery({
    queryKey: computed(() => ['item', s.wid, toValue(id)]),
    queryFn: () =>
      call(client.GET(`${INV}/items/{item_id}`, { params: { path: { workshop_id: s.wid, item_id: toValue(id) } } })),
    enabled: computed(() => !!s.wid && !!toValue(id)),
  })
}

export function useLocations() {
  const s = useSession()
  return useQuery({
    queryKey: computed(() => ['locations', s.wid]),
    queryFn: () => call(client.GET(`${INV}/locations`, { params: { path: { workshop_id: s.wid } } })),
    enabled: computed(() => !!s.wid),
    staleTime: 60_000,
  })
}

/** id → "Ford Transit › Бокс 2" (full path), and the default location's translated name. */
export function useLocationNames() {
  const { t } = useI18n()
  const { data } = useLocations()
  return computed(() => {
    const list = data.value ?? []
    const byId = new Map(list.map((l) => [l.id, l]))
    const name = (l: Location) => (l.is_default ? t('locations.main') : l.name)
    const path = (l: Location): string => {
      const parent = l.parent_id ? byId.get(l.parent_id) : undefined
      return parent ? `${path(parent)} › ${name(l)}` : name(l)
    }
    return new Map(list.map((l) => [l.id, path(l)]))
  })
}

export function useReorder() {
  const s = useSession()
  return useQuery({
    queryKey: computed(() => ['reorder', s.wid]),
    queryFn: () => call(client.GET(`${INV}/reorder`, { params: { path: { workshop_id: s.wid } } })),
    enabled: computed(() => !!s.wid),
  })
}

export function useCurrencies() {
  return useQuery({
    queryKey: ['currencies'],
    queryFn: () => call(client.GET('/api/v1/reference/currencies')),
    staleTime: Infinity,
  })
}

/** Every stock change goes through here: updates caches and offers Undo. */
export function useMove() {
  const qc = useQueryClient()
  const s = useSession()
  const toast = useToast()
  const { t } = useI18n()

  async function move(item: Pick<Item, 'id' | 'name'>, body: MovementBody) {
    const res = await call(
      client.POST(`${INV}/items/{item_id}/movements`, {
        params: { path: { workshop_id: s.wid, item_id: item.id } },
        body,
      }),
    )
    qc.setQueryData(['item', s.wid, item.id], res.item)
    qc.setQueriesData<{ items: Item[]; total: number }>({ queryKey: ['items', s.wid] }, (old) =>
      old ? { ...old, items: old.items.map((i) => (i.id === res.item.id ? res.item : i)) } : old,
    )
    qc.invalidateQueries({ queryKey: ['reorder', s.wid] })
    qc.invalidateQueries({ queryKey: ['movements', s.wid] })
    qc.invalidateQueries({ queryKey: ['locations', s.wid] })
    return res
  }

  /** Change + toast "−1 · name · Undo". Undo writes the opposite correction. */
  async function moveWithUndo(item: Pick<Item, 'id' | 'name'>, body: MovementBody, label: string) {
    try {
      const res = await move(item, body)
      const delta = res.movement.quantity
      toast.show(`${label} · ${item.name}`, {
        action:
          body.type === 'transfer' || delta === 0
            ? undefined
            : {
                label: t('common.undo'),
                run: () =>
                  move(item, { type: 'adjust', quantity: -delta, note: 'undo' })
                    .then(() => toast.show(t('stock.undone')))
                    .catch((e) => toast.error(errorText(e))),
              },
      })
      return res
    } catch (e) {
      toast.error(errorText(e))
      return null
    }
  }

  return { move, moveWithUndo }
}

export type AttributeField = Schemas['AttributeFieldOut']
export type Attributes = Record<string, unknown>

/** Characteristics fields per kind, as the admin set them (Admin → Characteristics). */
export function useAttributeSpec() {
  return useQuery({
    queryKey: ['attribute-spec'],
    queryFn: () => call(client.GET('/api/v1/catalog/attributes')),
    staleTime: 5 * 60_000,
  })
}

/** Label in the user's language; English, then Ukrainian when not translated. */
export function pickLabel(labels: Record<string, string> | undefined, locale: string): string {
  return labels?.[locale] || labels?.en || labels?.uk || ''
}

/** "Кнопок: 3", "Лезо: викидне" — labels and values in the user's language. */
export function useAttributeText() {
  const { t, locale } = useI18n()
  const { data: spec } = useAttributeSpec()
  const field = (kind: string, key: string) => spec.value?.[kind]?.find((f) => f.key === key)
  const label = (kind: string, key: string) => pickLabel(field(kind, key)?.labels, locale.value) || key
  const value = (kind: string, key: string, v: unknown) => {
    if (typeof v === 'boolean') return v ? t('attrs.yes') : t('attrs.no')
    const opt = field(kind, key)?.options.find((o) => o.key === String(v))
    return opt ? pickLabel(opt.labels, locale.value) : String(v)
  }
  return { label, value }
}
