<template>
  <PageHeader :title="t('admin.attrs.title')" :subtitle="t('admin.attrs.subtitle')">
    <UISelect v-model="kind" class="md:max-w-xs" :label="t('admin.attrs.kind')" :options="kindOptions" />
  </PageHeader>

  <div class="flex flex-col gap-3 p-3 md:p-0 md:pb-12">
    <p class="m-0 text-[14px] text-muted">{{ t('admin.attrs.rules') }}</p>
    <LoadError v-if="list.isError.value && !list.data.value" :error="list.error.value" @retry="list.refetch()" />
    <div v-else-if="list.isPending.value" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!fields.length" icon="list" :title="t('admin.attrs.none')" :text="t('admin.attrs.noneHint')" />

    <!-- Fields of the kind -->
    <article
      v-for="(f, i) in fields"
      :key="f.id"
      class="flex flex-col gap-3 rounded-card border bg-surface p-4"
      :class="f.is_hidden ? 'border-dashed border-line-strong opacity-70' : 'border-line'"
    >
      <div class="flex flex-wrap items-start gap-2">
        <div class="flex min-w-0 flex-1 flex-col">
          <b class="text-[17px]">{{ pickLabel(f.labels, locale) }}</b>
          <span class="text-[14px] text-muted">
            {{ t(`admin.attrs.types.${f.type}`) }}
            <template v-if="f.type === 'number' && (f.min_value !== null || f.max_value !== null)"> · {{ f.min_value ?? '…' }}–{{ f.max_value ?? '…' }}</template>
            · {{ t('admin.attrs.used', { n: f.used }) }}
            <b v-if="f.is_hidden" class="text-warn"> · {{ t('admin.attrs.hidden') }}</b>
          </span>
        </div>
        <div class="flex flex-wrap gap-1">
          <UIButton size="sm" variant="ghost" :disabled="i === 0" :aria-label="t('admin.attrs.up')" @click="move(i, -1)">↑</UIButton>
          <UIButton size="sm" variant="ghost" :disabled="i === fields.length - 1" :aria-label="t('admin.attrs.down')" @click="move(i, 1)">↓</UIButton>
          <UIButton size="sm" variant="outline" @click="toggleEdit(f)">{{ editing === f.id ? t('common.close') : t('common.edit') }}</UIButton>
          <UIButton size="sm" variant="outline" @click="patchField(f.id, { is_hidden: !f.is_hidden })">{{ f.is_hidden ? t('admin.attrs.show') : t('admin.attrs.hide') }}</UIButton>
          <UIButton v-if="!f.used" size="sm" variant="danger" @click="removeField(f.id)">{{ t('common.delete') }}</UIButton>
        </div>
      </div>

      <!-- Edit the field -->
      <form v-if="editing === f.id" class="flex flex-col gap-3 border-t border-ground pt-3" @submit.prevent="saveField(f)">
        <LabelsInput v-model="draft.labels" :label="t('admin.attrs.name')" :show-errors="tried" />
        <UISelect
          v-if="!f.used"
          v-model="draft.type"
          :label="t('admin.attrs.type')"
          :options="typeOptions"
        />
        <p v-else class="m-0 text-[14px] text-muted">{{ t('admin.attrs.typeLocked') }}</p>
        <div v-if="draft.type === 'number'" class="grid grid-cols-2 gap-2">
          <UIField v-model="draft.min" :label="t('admin.attrs.min')" inputmode="numeric" />
          <UIField v-model="draft.max" :label="t('admin.attrs.max')" inputmode="numeric" />
        </div>
        <UIButton type="submit" class="self-start">{{ t('common.save') }}</UIButton>
      </form>

      <!-- Values of a list field -->
      <div v-if="f.type === 'select'" class="flex flex-col gap-1 border-t border-ground pt-2">
        <span class="text-[14px] font-semibold text-muted">{{ t('admin.attrs.values') }}</span>
        <div v-for="(o, j) in f.options" :key="o.id" class="flex flex-col gap-2 border-b border-ground py-1.5 last:border-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="min-w-0 flex-1" :class="o.is_hidden ? 'text-muted line-through' : ''">
              {{ pickLabel(o.labels, locale) }}
              <span class="text-[13px] text-muted no-underline"> · {{ t('admin.attrs.used', { n: o.used }) }}</span>
            </span>
            <UIButton size="sm" variant="ghost" :disabled="j === 0" :aria-label="t('admin.attrs.up')" @click="moveOption(f, j, -1)">↑</UIButton>
            <UIButton size="sm" variant="ghost" :disabled="j === f.options.length - 1" :aria-label="t('admin.attrs.down')" @click="moveOption(f, j, 1)">↓</UIButton>
            <UIButton size="sm" variant="ghost" @click="toggleOption(o)">{{ editingOption === o.id ? t('common.close') : t('common.edit') }}</UIButton>
            <UIButton size="sm" variant="ghost" @click="patchOption(o.id, { is_hidden: !o.is_hidden })">{{ o.is_hidden ? t('admin.attrs.show') : t('admin.attrs.hide') }}</UIButton>
            <UIButton v-if="!o.used" size="sm" variant="danger" @click="removeOption(o.id)">{{ t('common.delete') }}</UIButton>
          </div>
          <form v-if="editingOption === o.id" class="flex flex-col gap-2" @submit.prevent="saveOption(o.id)">
            <LabelsInput v-model="optionDraft" :label="t('admin.attrs.value')" :show-errors="tried" />
            <UIButton type="submit" size="sm" class="self-start">{{ t('common.save') }}</UIButton>
          </form>
        </div>
        <form class="mt-2 flex flex-col gap-2 rounded-control bg-ground p-3" @submit.prevent="addOption(f.id)">
          <LabelsInput v-model="newOptions[f.id]" :label="t('admin.attrs.newValue')" />
          <UIButton type="submit" size="sm" class="self-start"><UIIcon name="plus" :size="16" />{{ t('admin.attrs.addValue') }}</UIButton>
        </form>
      </div>
    </article>

    <!-- New field -->
    <section class="flex flex-col gap-3 rounded-card border-2 border-dashed border-line-strong bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('admin.attrs.newField', { kind: t(`kinds.${kind}`) }) }}</h2>
      <form class="flex flex-col gap-3" novalidate @submit.prevent="createField">
        <LabelsInput v-model="create.labels" :label="t('admin.attrs.name')" :show-errors="createTried" />
        <UISelect v-model="create.type" :label="t('admin.attrs.type')" :options="typeOptions" />
        <div v-if="create.type === 'number'" class="grid grid-cols-2 gap-2">
          <UIField v-model="create.min" :label="t('admin.attrs.min')" inputmode="numeric" />
          <UIField v-model="create.max" :label="t('admin.attrs.max')" inputmode="numeric" />
        </div>
        <div v-if="create.type === 'select'" class="flex flex-col gap-2 rounded-control bg-ground p-3">
          <span class="text-[14px] text-muted">{{ t('admin.attrs.firstValueHint') }}</span>
          <LabelsInput v-model="create.option" :label="t('admin.attrs.newValue')" :show-errors="createTried" />
        </div>
        <UIButton type="submit" class="self-start"><UIIcon name="plus" :size="18" />{{ t('admin.attrs.addField') }}</UIButton>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIEmpty, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LabelsInput from '@/components/admin/LabelsInput.vue'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { KINDS } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { pickLabel } from '@/lib/queries'
import { useToast } from '@/stores/toast'

type FieldOut = Schemas['FieldAdminOut']
type Labels = Record<string, string>
type AttrType = 'select' | 'number' | 'bool'

const { t, locale } = useI18n()
const toast = useToast()
const qc = useQueryClient()

const kind = ref<string>('car_key')
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
const typeOptions = computed(() => (['select', 'number', 'bool'] as const).map((v) => ({ value: v, label: t(`admin.attrs.types.${v}`) })))

const list = useQuery({
  queryKey: computed(() => ['admin-attrs', kind.value]),
  queryFn: () => call(client.GET('/api/v1/admin/catalog/attributes', { params: { query: { kind: kind.value as never } } })),
})
const fields = computed<FieldOut[]>(() => list.data.value ?? [])

function refresh() {
  qc.invalidateQueries({ queryKey: ['admin-attrs'] })
  qc.invalidateQueries({ queryKey: ['attribute-spec'] }) // forms everywhere use the new list
}
async function run<T>(fn: () => Promise<T>, done?: string) {
  try {
    const out = await fn()
    refresh()
    if (done) toast.show(done)
    return out
  } catch (e) {
    toast.error(errorText(e))
    return null
  }
}
const num = (v: string) => (v.trim() === '' ? null : Number(v))
const filled = (l: Labels) => !!l.uk?.trim() && !!l.en?.trim()

// --- edit a field
const editing = ref<string | null>(null)
const tried = ref(false)
const draft = reactive({ labels: {} as Labels, type: 'select' as AttrType, min: '', max: '' })
function toggleEdit(f: FieldOut) {
  tried.value = false
  if (editing.value === f.id) return (editing.value = null)
  editing.value = f.id
  Object.assign(draft, { labels: { ...f.labels }, type: f.type as AttrType, min: f.min_value == null ? '' : String(f.min_value), max: f.max_value == null ? '' : String(f.max_value) })
}
async function saveField(f: FieldOut) {
  tried.value = true
  if (!filled(draft.labels)) return
  const body: Schemas['FieldUpdateIn'] = { labels: draft.labels, min_value: num(draft.min), max_value: num(draft.max) }
  if (!f.used) body.type = draft.type
  const ok = await run(() => call(client.PATCH('/api/v1/admin/catalog/attributes/{field_id}', { params: { path: { field_id: f.id } }, body })), t('common.saved'))
  if (ok) editing.value = null
}
const patchField = (id: string, body: Schemas['FieldUpdateIn']) =>
  run(() => call(client.PATCH('/api/v1/admin/catalog/attributes/{field_id}', { params: { path: { field_id: id } }, body })))
const removeField = (id: string) =>
  run(() => call(client.DELETE('/api/v1/admin/catalog/attributes/{field_id}', { params: { path: { field_id: id } } })), t('admin.attrs.deleted'))
function move(i: number, d: number) {
  const ids = fields.value.map((f) => f.id)
  ;[ids[i], ids[i + d]] = [ids[i + d], ids[i]]
  run(() => call(client.PUT('/api/v1/admin/catalog/attributes/order/{kind}', { params: { path: { kind: kind.value as never } }, body: { ids } })))
}

// --- values of list fields
const editingOption = ref<string | null>(null)
const optionDraft = ref<Labels>({})
function toggleOption(o: Schemas['OptionAdminOut']) {
  tried.value = false
  if (editingOption.value === o.id) return (editingOption.value = null)
  editingOption.value = o.id
  optionDraft.value = { ...o.labels }
}
async function saveOption(id: string) {
  tried.value = true
  if (!filled(optionDraft.value)) return
  const ok = await run(() => call(client.PATCH('/api/v1/admin/catalog/attributes/options/{option_id}', { params: { path: { option_id: id } }, body: { labels: optionDraft.value } })), t('common.saved'))
  if (ok) editingOption.value = null
}
const patchOption = (id: string, body: Schemas['OptionUpdateIn']) =>
  run(() => call(client.PATCH('/api/v1/admin/catalog/attributes/options/{option_id}', { params: { path: { option_id: id } }, body })))
const removeOption = (id: string) =>
  run(() => call(client.DELETE('/api/v1/admin/catalog/attributes/options/{option_id}', { params: { path: { option_id: id } } })), t('admin.attrs.deleted'))
function moveOption(f: FieldOut, j: number, d: number) {
  const ids = f.options.map((o) => o.id)
  ;[ids[j], ids[j + d]] = [ids[j + d], ids[j]]
  run(() => call(client.PUT('/api/v1/admin/catalog/attributes/{field_id}/options/order', { params: { path: { field_id: f.id } }, body: { ids } })))
}
const newOptions = reactive<Record<string, Labels>>({})
watch(fields, (list) => list.forEach((f) => (newOptions[f.id] ??= {})), { immediate: true })
async function addOption(fieldId: string) {
  const labels = newOptions[fieldId]
  if (!filled(labels)) return toast.error(t('admin.attrs.needUkEn'))
  const ok = await run(() => call(client.POST('/api/v1/admin/catalog/attributes/{field_id}/options', { params: { path: { field_id: fieldId } }, body: { labels } })))
  if (ok) newOptions[fieldId] = {}
}

// --- new field
const createTried = ref(false)
const empty = () => ({ labels: {} as Labels, type: 'select' as AttrType, min: '', max: '', option: {} as Labels })
const create = reactive(empty())
async function createField() {
  createTried.value = true
  if (!filled(create.labels) || (create.type === 'select' && !filled(create.option))) return
  const ok = await run(
    () =>
      call(
        client.POST('/api/v1/admin/catalog/attributes', {
          body: {
            kind: kind.value as never,
            type: create.type,
            labels: create.labels,
            min_value: create.type === 'number' ? num(create.min) : null,
            max_value: create.type === 'number' ? num(create.max) : null,
            options: create.type === 'select' ? [{ labels: create.option }] : [],
          },
        }),
      ),
    t('admin.attrs.created'),
  )
  if (ok) {
    Object.assign(create, empty())
    createTried.value = false
  }
}
</script>
