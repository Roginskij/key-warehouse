<template>
  <PageHeader
    :title="isEdit ? t('item.form.editTitle') : t('item.form.newTitle')"
    :back="isEdit ? { name: 'item', params: { id } } : { name: 'stock' }"
    :back-label="t('common.back')"
  />

  <!-- New item, step 1: find the key in the catalog -->
  <div v-if="mode === 'pick'" class="flex flex-col gap-3 p-4 md:max-w-2xl md:p-0 md:pb-12">
    <h2 class="m-0 text-[18px] font-bold">{{ t('item.pick.title') }}</h2>
    <CatalogPicker @pick="pick" @manual="startManual" />
  </div>

  <form v-else class="flex flex-col gap-4 p-4 md:max-w-2xl md:p-0 md:pb-12" novalidate @submit.prevent="submit">
    <!-- From the catalog: the card decides name, kind, numbers -->
    <section v-if="mode === 'catalog' && card" class="flex flex-col gap-2 rounded-card border-2 border-ink bg-surface p-4">
      <span class="flex items-center gap-2 text-[13px] font-semibold text-muted"><UIIcon name="check" :size="16" />{{ t('item.pick.fromCatalog') }}</span>
      <b class="text-[18px]">{{ card.name }}</b>
      <span class="text-[14px] text-muted">{{ t(`kinds.${card.kind}`) }}</span>
      <span class="text-[15px]">{{ card.codes.map((c) => `${c.brand} ${c.code}`).join(' · ') }}</span>
      <AttributesView :kind="card.kind" :values="card.attributes" class="mt-1" />
      <button v-if="!isEdit" type="button" class="self-start text-[15px] font-semibold underline" @click="mode = 'pick'">{{ t('item.pick.other') }}</button>
      <p v-else class="m-0 text-[13px] text-muted">{{ t('item.pick.lockedHint') }}</p>
    </section>

    <!-- Not in the catalog: brand from the list + number, goes to review -->
    <template v-else>
      <p v-if="!isEdit" class="m-0 rounded-control bg-primary-soft px-4 py-3 text-[15px]">{{ t('item.pick.manualHint') }}</p>
      <section class="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
        <UISelect v-model="form.brand" :label="t('item.form.brand')" :options="brandOptions" :error="errors.brand" />
        <UIField v-model="form.code" :label="t('item.form.code')" placeholder="HU66" :error="errors.code" />
        <!-- Maybe it is there after all -->
        <div v-if="similar.length" class="flex flex-col gap-2 rounded-control border-2 border-ink p-3 sm:col-span-2">
          <b class="text-[15px]">{{ t('item.pick.maybe') }}</b>
          <button
            v-for="c in similar"
            :key="c.id"
            type="button"
            class="flex items-center gap-3 rounded-control bg-ground px-3 py-2 text-left"
            @click="pick(c)"
          >
            <span class="flex min-w-0 flex-1 flex-col">
              <b class="truncate">{{ c.name }}</b>
              <span class="truncate text-[14px] text-muted">{{ c.codes.map((x) => `${x.brand} ${x.code}`).join(' · ') }}</span>
            </span>
            <span class="shrink-0 text-[14px] font-semibold">{{ t('item.pick.thisOne') }}</span>
          </button>
        </div>
        <UISelect v-model="form.kind" :label="t('item.form.kind')" :options="kindOptions" />
        <div class="flex flex-col gap-3 sm:col-span-2">
          <span v-if="hasAttrs" class="text-[15px] font-bold">{{ t('attrs.title') }}</span>
          <AttributesEditor v-model="form.attributes" :kind="form.kind" :error="attrError" />
        </div>
        <template v-if="electronic">
          <UIField v-model="form.frequency_mhz" :label="t('item.form.frequency')" inputmode="decimal" :decimals="3" placeholder="433.92" />
          <UIField v-model="form.chip_type" :label="t('item.form.chip')" placeholder="ID46" />
          <UIField v-model="form.fcc_id" label="FCC ID" />
        </template>
      </section>
    </template>

    <section class="rounded-card border border-line bg-surface p-4">
      <!-- What the workshop calls it; empty = the catalog name (or brand + number) -->
      <UIField
        v-model="form.name"
        :label="t('item.form.name')"
        :hint="t('item.form.nameHint')"
        :placeholder="card?.name ?? t('item.form.namePlaceholder')"
      />
    </section>

    <section v-if="!isEdit" class="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UIField v-model="form.quantity" :label="t('item.form.quantity')" inputmode="numeric" />
      <UISelect v-if="locOptions.length > 1" v-model="form.location_id" :label="t('item.form.location')" :options="locOptions" />
    </section>

    <section class="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UIField v-model="form.sale_price" :label="t('item.salePrice')" inputmode="decimal" :decimals="2" :error="errors.sale_price" />
      <UISelect v-model="form.sale_currency" :label="t('item.form.currency')" :options="curOptions" />
      <UIField v-model="form.cut_price" :label="t('item.cutPrice')" inputmode="decimal" :decimals="2" :hint="t('item.form.cutPriceHint')" :error="errors.cut_price" />
      <UISelect v-model="form.cut_currency" :label="t('item.form.currency')" :options="curOptions" />
      <UIField v-model="form.min_quantity" :label="t('item.form.min')" inputmode="numeric" :hint="t('item.form.minHint')" />
      <label class="flex items-start gap-3 sm:col-span-2">
        <input v-model="form.public_visible" type="checkbox" class="mt-0.5 size-5 shrink-0 accent-ink" />
        <span class="flex flex-col">
          <span class="text-[15px] font-semibold">{{ t('item.form.public') }}</span>
          <span class="text-[14px] text-muted">{{ t('item.form.publicHint') }}</span>
        </span>
      </label>
    </section>

    <section class="rounded-card border border-line bg-surface p-4">
      <label class="flex flex-col gap-1.5">
        <span class="text-[15px] font-semibold">{{ t('item.form.notes') }}</span>
        <textarea v-model="form.notes" rows="3" class="rounded-control border-2 border-line-strong p-3 text-[16px] outline-none focus:border-ink" />
      </label>
    </section>

    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">
      {{ error }}
      <RouterLink v-if="duplicateId" :to="{ name: 'item', params: { id: duplicateId } }" class="ml-1 font-bold text-danger">
        {{ t('item.form.openExisting') }}
      </RouterLink>
    </div>
    <UIButton type="submit" size="lg" block :loading="busy" class="md:w-auto md:self-start">{{ t('common.save') }}</UIButton>
  </form>
</template>

<script setup lang="ts">
import { ApiError, type Schemas } from '@kv/api'
import { UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AttributesEditor from '@/components/AttributesEditor.vue'
import AttributesView from '@/components/AttributesView.vue'
import PageHeader from '@/components/PageHeader.vue'
import CatalogPicker from '@/components/stock/CatalogPicker.vue'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { type Attributes, useAttributeSpec, useCurrencies, useItem, useLocationNames, useLocations } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

type Card = { id: string; name: string; kind: string; codes: { brand: string; code: string }[]; attributes?: Attributes }

const props = defineProps<{ id?: string }>()
const { t } = useI18n()
const router = useRouter()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const isEdit = computed(() => !!props.id)
const { data: existing } = useItem(() => props.id ?? '')
const { data: currencies } = useCurrencies()
const places = useLocationNames()

const KINDS = ['blank', 'car_key', 'remote', 'transponder', 'cylinder', 'key_shell', 'battery', 'machine', 'programmer', 'other'] as const

/** pick = searching the catalog; catalog = a card is chosen; manual = not in the catalog. */
const mode = ref<'pick' | 'catalog' | 'manual'>(isEdit.value ? 'manual' : 'pick')
const card = ref<Card | null>(null)

const form = ref({
  kind: 'blank' as string,
  name: '',
  brand: '',
  code: '',
  quantity: '0',
  location_id: null as string | null,
  sale_price: '',
  sale_currency: '',
  cut_price: '',
  cut_currency: '',
  min_quantity: '0',
  frequency_mhz: '',
  chip_type: '',
  fcc_id: '',
  attributes: {} as Attributes,
  notes: '',
  public_visible: false,
})

watch(
  existing,
  (it) => {
    if (!it || !isEdit.value) return
    Object.assign(form.value, {
      kind: it.kind,
      // Linked: only the workshop's own name (the catalog one is shown in the card above).
      name: it.catalog_item ? (it.my_name ?? '') : it.name,
      brand: it.brand ?? '',
      code: it.code ?? '',
      sale_price: it.sale_price ?? '',
      sale_currency: it.sale_currency ?? '',
      cut_price: it.cut_price ?? '',
      cut_currency: it.cut_currency ?? '',
      min_quantity: String(it.min_quantity),
      frequency_mhz: it.frequency_mhz ?? '',
      chip_type: it.chip_type ?? '',
      fcc_id: it.fcc_id ?? '',
      attributes: { ...(it.attributes ?? {}) },
      notes: it.notes ?? '',
      public_visible: it.public_visible,
    })
    if (it.catalog_item) {
      mode.value = 'catalog'
      card.value = { ...it.catalog_item, attributes: it.attributes }
    } else mode.value = 'manual'
  },
  { immediate: true },
)

function pick(c: Card) {
  card.value = c
  mode.value = 'catalog'
}
function startManual(typed: string) {
  mode.value = 'manual'
  card.value = null
  // What was searched is most likely the number.
  if (typed && !form.value.code) form.value.code = typed
}

// Brands: only from the catalog's list.
const brands = useQuery({
  queryKey: ['catalog-brands'],
  queryFn: () => call(client.GET('/api/v1/catalog/brands')),
  staleTime: 10 * 60_000,
})
const brandOptions = computed(() => [
  { value: '', label: t('item.pick.chooseBrand') },
  ...(brands.data.value ?? []).map((b) => ({ value: b.name, label: b.name })),
])

// While typing a number by hand: "maybe it is already in the catalog?"
const codeQ = ref('')
let timer: ReturnType<typeof setTimeout>
watch(
  () => form.value.code,
  (v) => {
    clearTimeout(timer)
    timer = setTimeout(() => (codeQ.value = v.trim()), 300)
  },
)
const similarQuery = useQuery({
  queryKey: computed(() => ['catalog-similar', codeQ.value]),
  queryFn: () => call(client.GET('/api/v1/catalog/items', { params: { query: { q: codeQ.value, limit: 3 } } })),
  enabled: computed(() => mode.value === 'manual' && codeQ.value.length >= 3),
})
const similar = computed(() => (mode.value === 'manual' && codeQ.value.length >= 3 ? (similarQuery.data.value?.items ?? []) : []))

const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
const curOptions = computed(() => [
  { value: '', label: t('item.form.baseCurrency') },
  ...(currencies.value ?? []).map((c) => ({ value: c.code, label: c.code })),
])
const locOptions = computed(() => [...places.value].map(([value, label]) => ({ value, label })))
// New items go to the main place unless the user picks another.
const { data: locations } = useLocations()
watch(
  locations,
  (list) => {
    if (!form.value.location_id && list?.length) form.value.location_id = (list.find((l) => l.is_default) ?? list[0]).id
  },
  { immediate: true },
)
const electronic = computed(() => ['car_key', 'remote', 'transponder'].includes(form.value.kind))

const errors = ref<Record<string, string>>({})
const attrError = ref<string | null>(null)
const { data: attrSpec } = useAttributeSpec()
const hasAttrs = computed(() => (attrSpec.value?.[form.value.kind] ?? []).length > 0)
const error = ref('')
const duplicateId = ref<string | null>(null)
const busy = ref(false)

const dec = (v: string) => (v.trim() ? v.replace(',', '.').replace(/\s/g, '') : null)
const int = (v: string) => Math.max(0, Math.round(Number(v.replace(',', '.')) || 0))
const txt = (v: string) => (v.trim() ? v.trim() : null)

function validManual(): boolean {
  const f = form.value
  if (!f.brand) errors.value.brand = t('validation.missing')
  if (!f.code.trim()) errors.value.code = t('validation.missing')
  return !Object.keys(errors.value).length
}

async function submit() {
  errors.value = {}
  error.value = ''
  duplicateId.value = null
  attrError.value = null
  const manual = mode.value === 'manual'
  if (manual && !validManual()) return
  busy.value = true
  const f = form.value
  // Always the workshop's own fields; the catalog's ones only for an item not in the catalog.
  const body: Record<string, unknown> = {
    name: txt(f.name),
    sale_price: dec(f.sale_price),
    sale_currency: f.sale_price.trim() ? f.sale_currency || null : null,
    cut_price: dec(f.cut_price),
    cut_currency: f.cut_price.trim() ? f.cut_currency || null : null,
    min_quantity: int(f.min_quantity),
    notes: txt(f.notes),
    public_visible: f.public_visible,
  }
  if (manual) {
    Object.assign(body, {
      kind: f.kind,
      brand: f.brand,
      code: f.code.trim(),
      frequency_mhz: electronic.value ? dec(f.frequency_mhz) : null,
      chip_type: electronic.value ? txt(f.chip_type) : null,
      fcc_id: electronic.value ? txt(f.fcc_id) : null,
      attributes: f.attributes,
    })
  }
  try {
    const path = { workshop_id: session.wid }
    if (isEdit.value) {
      const it = await call(
        client.PATCH('/api/v1/workshops/{workshop_id}/inventory/items/{item_id}', {
          params: { path: { ...path, item_id: props.id! } },
          body: body as Schemas['StockItemUpdateIn'],
        }),
      )
      qc.setQueryData(['item', session.wid, it.id], it)
      qc.invalidateQueries({ queryKey: ['items', session.wid] })
      router.replace({ name: 'item', params: { id: it.id } })
    } else {
      if (!manual && card.value) body.catalog_item_id = card.value.id
      const it = await call(
        client.POST('/api/v1/workshops/{workshop_id}/inventory/items', {
          params: { path },
          body: { ...body, quantity: int(f.quantity), location_id: f.location_id } as Schemas['StockItemCreateIn'],
        }),
      )
      qc.invalidateQueries({ queryKey: ['items', session.wid] })
      qc.invalidateQueries({ queryKey: ['reorder', session.wid] })
      if (manual && it.catalog === 'linked') toast.show(t('item.form.linked'))
      else if (it.catalog === 'proposed') toast.show(t('item.form.proposed'))
      router.replace({ name: 'item', params: { id: it.id } })
    }
  } catch (e) {
    errors.value = fieldErrors(e)
    if (e instanceof ApiError && e.code === 'catalog.bad_attribute') attrError.value = String(e.params.field)
    if (e instanceof ApiError && e.code === 'inventory.duplicate') duplicateId.value = String(e.params.item_id)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
