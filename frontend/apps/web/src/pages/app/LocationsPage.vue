<template>
  <PageHeader :title="t('locations.title')" :subtitle="t('locations.subtitle')">
    <template #actions>
      <UIButton variant="on-graphite" class="md:border md:border-line-strong md:bg-surface md:text-ink" @click="scanOpen = true">
        <UIIcon name="scan" :size="18" />{{ t('scan.button') }}
      </UIButton>
      <RouterLink :to="{ name: 'labels' }" :class="buttonClass('on-graphite', 'md')" class="md:border md:border-line-strong md:bg-surface md:text-ink">
        <UIIcon name="qr" :size="18" />{{ t('labels.button') }}
      </RouterLink>
      <div class="hidden md:block">
        <UIButton @click="openNew()"><UIIcon name="plus" :size="18" :stroke="2.6" />{{ t('locations.add') }}</UIButton>
      </div>
    </template>
  </PageHeader>
  <div class="flex flex-col gap-3 p-2.5 md:max-w-3xl md:p-0 md:pb-10">
    <LoadError v-if="isError && !data" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!rows.length" icon="pin" :title="t('locations.emptyTitle')" :text="t('locations.emptyText')">
      <UIButton @click="openNew()"><UIIcon name="plus" :size="18" :stroke="2.6" />{{ t('locations.add') }}</UIButton>
    </UIEmpty>
    <ul v-else class="m-0 list-none divide-y divide-ground overflow-hidden rounded-card border border-line bg-surface p-0">
      <li v-for="r in rows" :key="r.loc.id" class="flex min-h-14 items-center gap-2 pr-2">
        <RouterLink
          :to="{ name: 'stock', query: { location: r.loc.id } }"
          class="flex min-w-0 flex-1 items-center gap-3 py-2 text-ink no-underline"
          :style="{ paddingLeft: `${14 + r.depth * 22}px` }"
        >
          <span v-if="r.depth === 0" class="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-primary-soft">
            <UIIcon :name="ICON[r.loc.kind] ?? 'pin'" :size="22" />
          </span>
          <span v-else class="-mt-2.5 size-3 shrink-0 border-b-2 border-l-2 border-line-strong" aria-hidden="true" />
          <span class="flex min-w-0 flex-col">
            <span class="truncate" :class="r.depth === 0 ? 'text-[17px] font-bold' : 'text-[16px] font-medium'">{{ label(r.loc) }}</span>
            <span v-if="r.depth === 0" class="text-[14px] text-muted">{{ t(`locations.kinds.${r.loc.kind}`) }}</span>
          </span>
          <span class="ml-auto shrink-0 pl-2 font-semibold">{{ t('common.pcs', { n: num(r.total) }) }}</span>
        </RouterLink>
        <button type="button" class="flex size-10 shrink-0 items-center justify-center rounded-full text-muted hover:bg-black/5" :aria-label="t('common.edit')" @click="openEdit(r.loc)">
          <UIIcon name="edit" :size="18" />
        </button>
      </li>
    </ul>
    <div class="md:hidden">
      <UIButton variant="outline" size="lg" block class="border-2 border-dashed" @click="openNew()">
        <UIIcon name="plus" :size="20" :stroke="2.6" />{{ t('locations.add') }}
      </UIButton>
    </div>
  </div>

  <ScanSheet v-if="scanOpen" :open="scanOpen" @close="scanOpen = false" />
  <Sheet :open="sheetOpen" :title="editing ? t('locations.editTitle') : t('locations.add')" :close-label="t('common.close')" @close="sheetOpen = false">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="save">
      <UIField v-if="!editing?.is_default" v-model="form.name" :label="t('locations.name')" :placeholder="t('locations.namePlaceholder')" />
      <UISelect v-model="form.kind" :label="t('locations.kind')" :options="kindOptions" />
      <UISelect v-if="!editing?.is_default" v-model="form.parent_id" :label="t('locations.inside')" :options="parentOptions" />
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('common.save') }}</UIButton>
      <UIButton v-if="editing && !editing.is_default" variant="danger" block @click="remove">
        <UIIcon name="trash" :size="18" />{{ t('common.delete') }}
      </UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIEmpty, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import ScanSheet from '@/components/ScanSheet.vue'
import Sheet from '@/components/Sheet.vue'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { num } from '@/lib/format'
import { type Location, useLocations } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const { data, isPending, isError, error, refetch } = useLocations()

const KINDS = ['room', 'rack', 'shelf', 'box', 'vehicle', 'other'] as const
const ICON: Record<string, string> = { room: 'home', vehicle: 'car', rack: 'box', shelf: 'box', box: 'box', other: 'pin' }
const label = (l: Location) => (l.is_default ? t('locations.main') : l.name)

interface Node { loc: Location; depth: number; total: number }
// Flatten the tree in display order; totals include everything inside.
const rows = computed<Node[]>(() => {
  const list = data.value ?? []
  const kids = new Map<string | null, Location[]>()
  for (const l of list) kids.set(l.parent_id, [...(kids.get(l.parent_id) ?? []), l])
  const total = (l: Location): number => l.pieces + (kids.get(l.id) ?? []).reduce((s, c) => s + total(c), 0)
  const out: Node[] = []
  const walk = (parent: string | null, depth: number) => {
    for (const l of kids.get(parent) ?? []) {
      out.push({ loc: l, depth, total: total(l) })
      walk(l.id, depth + 1)
    }
  }
  walk(null, 0)
  return out
})

const scanOpen = ref(false)
const sheetOpen = ref(false)
const editing = ref<Location | null>(null)
const form = ref({ name: '', kind: 'box' as string, parent_id: '' })
const busy = ref(false)

function openNew(parent?: Location) {
  editing.value = null
  form.value = { name: '', kind: parent ? 'box' : 'room', parent_id: parent?.id ?? '' }
  sheetOpen.value = true
}
function openEdit(l: Location) {
  editing.value = l
  form.value = { name: l.name, kind: l.kind, parent_id: l.parent_id ?? '' }
  sheetOpen.value = true
}
const parentOptions = computed(() => [
  { value: '', label: t('locations.topLevel') },
  ...rows.value
    .filter((r) => r.loc.id !== editing.value?.id)
    .map((r) => ({ value: r.loc.id, label: `${'— '.repeat(r.depth)}${label(r.loc)}` })),
])
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`locations.kinds.${k}`) })))

async function save() {
  if (!form.value.name.trim() && !editing.value?.is_default) return
  busy.value = true
  const body = { name: form.value.name.trim(), kind: form.value.kind as Location['kind'], parent_id: form.value.parent_id || null }
  try {
    const path = { workshop_id: session.wid }
    if (editing.value)
      await call(client.PATCH('/api/v1/workshops/{workshop_id}/inventory/locations/{location_id}', {
        params: { path: { ...path, location_id: editing.value.id } }, body: body as never,
      }))
    else await call(client.POST('/api/v1/workshops/{workshop_id}/inventory/locations', { params: { path }, body: body as never }))
    sheetOpen.value = false
    qc.invalidateQueries({ queryKey: ['locations', session.wid] })
  } catch (e) {
    toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!editing.value) return
  try {
    await call(client.DELETE('/api/v1/workshops/{workshop_id}/inventory/locations/{location_id}', {
      params: { path: { workshop_id: session.wid, location_id: editing.value.id } },
    }))
    sheetOpen.value = false
    qc.invalidateQueries({ queryKey: ['locations', session.wid] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
