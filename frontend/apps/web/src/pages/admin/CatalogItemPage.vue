<template>
  <PageHeader :title="item?.name ?? '…'" :back="{ name: 'admin-catalog' }" :back-label="t('admin.nav.catalog')">
    <template v-if="item" #actions>
      <span class="rounded-md px-2 py-0.5 text-sm font-semibold" :class="item.status === 'active' ? 'bg-primary-soft text-ink' : 'bg-warn-bg text-warn'">
        {{ t(`admin.status.${item.status}`) }}
      </span>
    </template>
  </PageHeader>

  <div v-if="isError && !item" class="p-3 md:p-0"><LoadError :error="error" @retry="refetch()" /></div>
  <div v-else-if="isPending" class="m-3 h-40 animate-pulse rounded-card bg-surface md:mx-0" />

  <div v-else-if="item" class="grid gap-4 p-3 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
    <div class="flex flex-col gap-4">
      <p v-if="item.status === 'merged' && item.merged_into_id" class="m-0 rounded-card border border-line bg-warn-bg p-4 text-warn">
        {{ t('admin.item.mergedInto') }}
        <RouterLink :to="{ name: 'admin-item', params: { id: item.merged_into_id } }" class="font-bold text-warn">{{ t('admin.item.open') }}</RouterLink>
      </p>

      <!-- Codes -->
      <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ t('admin.item.codes') }}</h2>
        <p class="m-0 text-[14px] text-muted">{{ t('admin.item.codesHint') }}</p>
        <ul class="m-0 flex list-none flex-col divide-y divide-ground p-0">
          <li v-for="c in item.codes" :key="c.id" class="flex items-center gap-3 py-2">
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="font-semibold">{{ c.brand }} {{ c.code }}</span>
              <span class="text-[13px] text-muted">
                {{ t(`admin.source.${c.source_type}`) }}<template v-if="c.source_ref && !c.source_ref.startsWith('proposal:')"> · {{ c.source_ref }}</template>
                <template v-if="c.confirmations"> · {{ t('admin.item.confirmations', { n: c.confirmations }) }}</template>
              </span>
            </span>
            <button
              v-if="canEdit && item.status === 'active'"
              type="button"
              class="flex size-10 items-center justify-center rounded-full text-danger hover:bg-danger-bg"
              :aria-label="t('admin.item.removeCode', { code: `${c.brand} ${c.code}` })"
              @click="removeCode(c.id)"
            ><UIIcon name="trash" :size="18" /></button>
          </li>
        </ul>
        <form v-if="canEdit && item.status === 'active'" class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto] gap-2" @submit.prevent="addCode">
          <select v-model="newBrand" :aria-label="t('item.form.brand')" class="h-11 rounded-control border-2 border-line-strong bg-surface px-2">
            <option value="" disabled>{{ t('item.form.brand') }}</option>
            <option v-for="b in brands?.filter((x) => x.is_active)" :key="b.id" :value="b.name">{{ b.name }}</option>
          </select>
          <input v-model="newCode" :aria-label="t('item.form.code')" :placeholder="t('item.form.code')" class="h-11 min-w-0 rounded-control border-2 border-line-strong px-3 outline-none focus:border-ink" />
          <UIButton type="submit">{{ t('admin.item.add') }}</UIButton>
        </form>
        <UIButton v-if="canEdit && item.codes.length > 1 && item.status === 'active'" size="sm" variant="ghost" class="self-start underline" @click="splitOpen = true">
          {{ t('admin.item.split') }}
        </UIButton>
      </section>

      <!-- Substitutes -->
      <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ t('admin.item.substitutes') }}</h2>
        <div class="flex flex-col gap-1">
          <span class="text-[14px] font-semibold text-muted">{{ t('admin.item.replacedBy') }}</span>
          <p v-if="!item.can_be_replaced_by.length" class="m-0 text-[15px] text-muted">—</p>
          <div v-for="s in item.can_be_replaced_by" :key="s.id" class="flex items-center gap-2">
            <RouterLink :to="{ name: 'admin-item', params: { id: s.id } }" class="min-w-0 flex-1 truncate font-semibold text-ink">{{ s.name }} <span class="font-normal text-muted">· {{ codesLabel(s) }}</span></RouterLink>
            <button v-if="canEdit" type="button" class="flex size-9 items-center justify-center rounded-full text-danger hover:bg-danger-bg" :aria-label="t('common.delete')" @click="removeSubstitute(item.id, s.id)"><UIIcon name="close" :size="18" /></button>
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-[14px] font-semibold text-muted">{{ t('admin.item.replaces') }}</span>
          <p v-if="!item.can_replace.length" class="m-0 text-[15px] text-muted">—</p>
          <div v-for="s in item.can_replace" :key="s.id" class="flex items-center gap-2">
            <RouterLink :to="{ name: 'admin-item', params: { id: s.id } }" class="min-w-0 flex-1 truncate font-semibold text-ink">{{ s.name }} <span class="font-normal text-muted">· {{ codesLabel(s) }}</span></RouterLink>
            <button v-if="canEdit" type="button" class="flex size-9 items-center justify-center rounded-full text-danger hover:bg-danger-bg" :aria-label="t('common.delete')" @click="removeSubstitute(s.id, item.id)"><UIIcon name="close" :size="18" /></button>
          </div>
        </div>
        <div v-if="canEdit && item.status === 'active'" class="flex flex-col gap-2 border-t border-ground pt-3">
          <UISelect
            v-model="subDirection"
            :label="t('admin.item.addSubstitute')"
            :options="[
              { value: 'replaced_by', label: t('admin.item.dirReplacedBy') },
              { value: 'replaces', label: t('admin.item.dirReplaces') },
            ]"
          />
          <ItemPicker :label="t('admin.item.findItem')" :placeholder="t('admin.catalog.search')" :exclude-id="item.id" @pick="addSubstitute" />
        </div>
      </section>

      <ItemPublicSections :item="item" :can-edit="canEdit" @updated="(d) => done(d)" />
    </div>

    <div class="flex flex-col gap-4">
      <!-- Fields -->
      <form class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4" @submit.prevent="saveFields">
        <h2 class="m-0 text-[17px] font-bold">{{ t('admin.item.details') }}</h2>
        <fieldset :disabled="!canEdit || item.status === 'merged'" class="m-0 flex flex-col gap-4 border-0 p-0">
          <UISelect v-model="form.kind" :label="t('item.form.kind')" :options="kindOptions" />
          <UIField v-model="form.name" :label="t('item.form.name')" />
          <label class="flex flex-col gap-1.5">
            <span class="text-[15px] font-semibold">{{ t('admin.item.description') }}</span>
            <textarea v-model="form.description" rows="3" class="rounded-control border-2 border-line-strong p-3 text-[16px] outline-none focus:border-ink" />
          </label>
          <div class="grid gap-3 sm:grid-cols-3">
            <UIField v-model="form.frequency_mhz" :label="t('item.form.frequency')" inputmode="decimal" />
            <UIField v-model="form.chip_type" :label="t('item.form.chip')" />
            <UIField v-model="form.fcc_id" label="FCC ID" />
          </div>
        </fieldset>
        <div v-if="canEdit && item.status !== 'merged'" class="flex flex-wrap gap-2">
          <UIButton type="submit">{{ t('common.save') }}</UIButton>
          <UIButton v-if="item.status === 'active'" variant="danger" @click="setStatus('archived')">{{ t('admin.item.archive') }}</UIButton>
          <UIButton v-else variant="outline" @click="setStatus('active')">{{ t('admin.item.restore') }}</UIButton>
        </div>
        <p v-if="item.slug" class="m-0 text-[14px]">
          {{ t('admin.item.publicPage') }}:
          <a :href="`${shopUrl}/uk/keys/${item.slug}`" target="_blank" rel="noopener" class="font-semibold text-ink">/keys/{{ item.slug }}</a>
          <span class="block text-[13px] text-muted">{{ t('admin.item.publicPageHint') }}</span>
        </p>
        <p class="m-0 text-[13px] text-muted">
          {{ t(`admin.source.${item.source_type}`) }}<template v-if="item.source_ref && !item.source_ref.startsWith('proposal:')"> · {{ item.source_ref }}</template> · {{ dateTime(item.created_at) }}
        </p>
      </form>

      <!-- Merge -->
      <section v-if="canEdit && item.status === 'active'" class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ t('admin.item.mergeTitle') }}</h2>
        <p class="m-0 text-[14px] text-muted">{{ t('admin.item.mergeHint') }}</p>
        <ItemPicker :label="t('admin.item.findDuplicate')" :placeholder="t('admin.catalog.search')" :exclude-id="item.id" @pick="(i) => (mergeCandidate = i)" />
      </section>

      <!-- History -->
      <section class="flex flex-col gap-2 px-1">
        <h2 class="m-0 text-[16px] font-bold">{{ t('item.history') }}</h2>
        <p v-if="!history.data.value?.length" class="m-0 text-muted">{{ t('item.noHistory') }}</p>
        <p v-for="h in history.data.value" :key="h.id" class="m-0 text-[14px]">
          <span class="text-muted">{{ dateTime(h.created_at) }} ·</span> {{ t(`admin.actions.${h.action.replace('.', '_')}`) }}
          <span class="text-muted">{{ Object.entries(h.data).filter(([k]) => ['brand', 'code', 'name', 'source'].includes(k)).map(([, v]) => v).join(' ') }}</span>
        </p>
      </section>
    </div>
  </div>

  <Sheet :open="!!mergeCandidate" :title="t('admin.item.mergeConfirmTitle')" :close-label="t('common.close')" @close="mergeCandidate = null">
    <p class="m-0">{{ t('admin.item.mergeConfirm', { dup: mergeCandidate?.name ?? '', main: item?.name ?? '' }) }}</p>
    <p class="m-0 text-[14px] text-muted">{{ mergeCandidate ? codesLabel(mergeCandidate) : '' }}</p>
    <UIButton size="lg" block @click="confirmMerge">{{ t('admin.item.mergeButton') }}</UIButton>
  </Sheet>

  <Sheet :open="splitOpen" :title="t('admin.item.split')" :close-label="t('common.close')" @close="splitOpen = false">
    <form v-if="item" class="flex flex-col gap-3" @submit.prevent="confirmSplit">
      <p class="m-0 text-[15px] text-muted">{{ t('admin.item.splitHint') }}</p>
      <label v-for="c in item.codes" :key="c.id" class="flex items-center gap-3 rounded-control border border-line p-3">
        <input v-model="splitCodes" type="checkbox" :value="c.id" class="size-5 accent-ink" />{{ c.brand }} {{ c.code }}
      </label>
      <UIField v-model="splitName" :label="t('admin.item.newName')" />
      <UIButton type="submit" size="lg" block :disabled="!splitCodes.length || splitCodes.length >= item.codes.length">{{ t('admin.item.splitButton') }}</UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ItemPicker from '@/components/admin/ItemPicker.vue'
import ItemPublicSections from '@/components/admin/ItemPublicSections.vue'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import Sheet from '@/components/Sheet.vue'
import { KINDS, useBrands } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { dateTime } from '@/lib/format'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

type Detail = Schemas['ItemAdminDetailOut']
type Brief = { id: string; name: string; codes: { brand: string; code: string }[] }

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const canEdit = computed(() => session.can('catalog.edit'))
const { data: brands } = useBrands()
const shopUrl = import.meta.env.VITE_SHOP_URL ?? 'http://localhost:3000'

const key = computed(() => ['admin-item', props.id])
const { data: item, isPending, isError, error, refetch } = useQuery({
  queryKey: key,
  queryFn: () => call(client.GET('/api/v1/admin/catalog/items/{item_id}', { params: { path: { item_id: props.id } } })),
})
const history = useQuery({
  queryKey: computed(() => ['admin-item-history', props.id]),
  queryFn: () => call(client.GET('/api/v1/admin/catalog/audit', { params: { query: { entity_id: props.id, limit: 20 } } })),
})

function done(updated: Detail, message?: string) {
  qc.setQueryData(key.value, updated)
  qc.invalidateQueries({ queryKey: ['admin-catalog'] })
  qc.invalidateQueries({ queryKey: ['admin-item-history', props.id] })
  if (message) toast.show(message)
}
async function act(fn: () => Promise<Detail>, message?: string) {
  try {
    done(await fn(), message)
    return true
  } catch (e) {
    toast.error(errorText(e))
    return false
  }
}
const itemPath = computed(() => ({ item_id: props.id }))

// --- fields
const form = ref({ kind: 'blank', name: '', description: '', frequency_mhz: '', chip_type: '', fcc_id: '' })
watch(
  item,
  (it) => {
    if (!it) return
    form.value = {
      kind: it.kind,
      name: it.name,
      description: it.description ?? '',
      frequency_mhz: it.frequency_mhz ?? '',
      chip_type: it.chip_type ?? '',
      fcc_id: it.fcc_id ?? '',
    }
  },
  { immediate: true },
)
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
const txt = (v: string) => (v.trim() ? v.trim() : null)
function saveFields() {
  return act(
    () =>
      call(
        client.PATCH('/api/v1/admin/catalog/items/{item_id}', {
          params: { path: itemPath.value },
          body: {
            kind: form.value.kind as never,
            name: form.value.name.trim(),
            description: txt(form.value.description),
            frequency_mhz: txt(form.value.frequency_mhz.replace(',', '.')),
            chip_type: txt(form.value.chip_type),
            fcc_id: txt(form.value.fcc_id),
          },
        }),
      ),
    t('admin.item.saved'),
  )
}
function setStatus(status: 'active' | 'archived') {
  return act(
    () => call(client.PATCH('/api/v1/admin/catalog/items/{item_id}', { params: { path: itemPath.value }, body: { status } })),
    status === 'archived' ? t('admin.item.archivedMsg') : t('admin.item.restoredMsg'),
  )
}

// --- codes
const newBrand = ref('')
const newCode = ref('')
async function addCode() {
  if (!newBrand.value || !newCode.value.trim()) return
  const ok = await act(() =>
    call(
      client.POST('/api/v1/admin/catalog/items/{item_id}/codes', {
        params: { path: itemPath.value },
        body: { brand: newBrand.value, code: newCode.value.trim() },
      }),
    ),
  )
  if (ok) newCode.value = ''
}
function removeCode(codeId: string) {
  return act(() =>
    call(client.DELETE('/api/v1/admin/catalog/items/{item_id}/codes/{code_id}', { params: { path: { ...itemPath.value, code_id: codeId } } })),
  )
}

// --- substitutes
const subDirection = ref<'replaced_by' | 'replaces'>('replaced_by')
function addSubstitute(other: Brief) {
  const body =
    subDirection.value === 'replaced_by'
      ? { item_id: props.id, substitute_item_id: other.id }
      : { item_id: other.id, substitute_item_id: props.id }
  return act(async () => {
    await call(client.POST('/api/v1/admin/catalog/substitutes', { body }))
    return call(client.GET('/api/v1/admin/catalog/items/{item_id}', { params: { path: itemPath.value } }))
  })
}
function removeSubstitute(itemId: string, subId: string) {
  return act(async () => {
    await call(
      client.DELETE('/api/v1/admin/catalog/substitutes/{item_id}/{substitute_item_id}', {
        params: { path: { item_id: itemId, substitute_item_id: subId } },
      }),
    )
    return call(client.GET('/api/v1/admin/catalog/items/{item_id}', { params: { path: itemPath.value } }))
  })
}

// --- merge
const mergeCandidate = ref<Brief | null>(null)
async function confirmMerge() {
  const other = mergeCandidate.value
  if (!other) return
  mergeCandidate.value = null
  await act(
    () =>
      call(
        client.POST('/api/v1/admin/catalog/items/{item_id}/merge', {
          params: { path: itemPath.value },
          body: { source_item_ids: [other.id] },
        }),
      ),
    t('admin.item.merged', { name: other.name }),
  )
}

// --- split
const splitOpen = ref(false)
const splitCodes = ref<string[]>([])
const splitName = ref('')
async function confirmSplit() {
  try {
    const created = await call(
      client.POST('/api/v1/admin/catalog/items/{item_id}/split', {
        params: { path: itemPath.value },
        body: { code_ids: splitCodes.value, name: txt(splitName.value) },
      }),
    )
    splitOpen.value = false
    splitCodes.value = []
    splitName.value = ''
    qc.invalidateQueries({ queryKey: key.value })
    qc.invalidateQueries({ queryKey: ['admin-catalog'] })
    toast.show(t('admin.item.splitDone', { name: created.name }))
  } catch (e) {
    toast.error(errorText(e))
  }
}

const codesLabel = (i: Brief) => i.codes.map((c) => `${c.brand} ${c.code}`).join(' · ')
</script>
