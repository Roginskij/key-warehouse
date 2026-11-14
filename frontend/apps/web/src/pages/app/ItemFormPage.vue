<template>
  <PageHeader
    :title="isEdit ? t('item.form.editTitle') : t('item.form.newTitle')"
    :back="isEdit ? { name: 'item', params: { id } } : { name: 'stock' }"
    :back-label="t('common.back')"
  />
  <form class="flex flex-col gap-4 p-4 md:max-w-2xl md:p-0 md:pb-12" novalidate @submit.prevent="submit">
    <section class="grid gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UISelect v-model="form.kind" :label="t('item.form.kind')" :options="kindOptions" />
      <UIField v-model="form.name" class="sm:col-span-2" :label="t('item.form.name')" :placeholder="t('item.form.namePlaceholder')" :error="errors.name" />
      <UIField v-model="form.brand" :label="t('item.form.brand')" placeholder="Silca" :error="errors.brand" />
      <UIField v-model="form.code" :label="t('item.form.code')" placeholder="HU66" :error="errors.code" />
      <UIField v-model="form.vehicles" class="sm:col-span-2" :label="t('item.form.vehicles')" :placeholder="t('item.form.vehiclesPlaceholder')" />
    </section>

    <section v-if="!isEdit" class="grid gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UIField v-model="form.quantity" :label="t('item.form.quantity')" inputmode="numeric" />
      <UISelect v-if="locOptions.length > 1" v-model="form.location_id" :label="t('item.form.location')" :options="locOptions" />
    </section>

    <section class="grid gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UIField v-model="form.sale_price" :label="t('item.salePrice')" inputmode="decimal" :error="errors.sale_price" />
      <UISelect v-model="form.sale_currency" :label="t('item.form.currency')" :options="curOptions" />
      <template v-if="session.seesPurchase">
        <UIField v-model="form.purchase_price" :label="t('item.purchasePrice')" inputmode="decimal" :error="errors.purchase_price" />
        <UISelect v-model="form.purchase_currency" :label="t('item.form.currency')" :options="curOptions" />
      </template>
      <UIField v-model="form.min_quantity" :label="t('item.form.min')" inputmode="numeric" :hint="t('item.form.minHint')" />
      <label class="flex items-start gap-3 sm:col-span-2">
        <input v-model="form.public_visible" type="checkbox" class="mt-0.5 size-5 shrink-0 accent-ink" />
        <span class="flex flex-col">
          <span class="text-[15px] font-semibold">{{ t('item.form.public') }}</span>
          <span class="text-[14px] text-muted">{{ t('item.form.publicHint') }}</span>
        </span>
      </label>
    </section>

    <section v-if="electronic" class="grid gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-3">
      <UIField v-model="form.frequency_mhz" :label="t('item.form.frequency')" inputmode="decimal" placeholder="433.92" />
      <UIField v-model="form.chip_type" :label="t('item.form.chip')" placeholder="ID46" />
      <UIField v-model="form.fcc_id" label="FCC ID" />
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
import { UIButton, UIField, UISelect } from '@kv/ui'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { useCurrencies, useItem, useLocationNames, useLocations } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

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

const form = ref({
  kind: 'blank' as (typeof KINDS)[number],
  name: '',
  brand: '',
  code: '',
  vehicles: '',
  quantity: '0',
  location_id: null as string | null,
  sale_price: '',
  sale_currency: '',
  purchase_price: '',
  purchase_currency: '',
  min_quantity: '0',
  frequency_mhz: '',
  chip_type: '',
  fcc_id: '',
  notes: '',
  public_visible: false,
})

watch(
  existing,
  (it) => {
    if (!it || !isEdit.value) return
    Object.assign(form.value, {
      kind: it.kind,
      name: it.name,
      brand: it.brand ?? '',
      code: it.code ?? '',
      vehicles: it.vehicles ?? '',
      sale_price: it.sale_price ?? '',
      sale_currency: it.sale_currency ?? '',
      purchase_price: it.purchase_price ?? '',
      purchase_currency: it.purchase_currency ?? '',
      min_quantity: String(it.min_quantity),
      frequency_mhz: it.frequency_mhz ?? '',
      chip_type: it.chip_type ?? '',
      fcc_id: it.fcc_id ?? '',
      notes: it.notes ?? '',
      public_visible: it.public_visible,
    })
  },
  { immediate: true },
)

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
const error = ref('')
const duplicateId = ref<string | null>(null)
const busy = ref(false)

const dec = (v: string) => (v.trim() ? v.replace(',', '.').replace(/\s/g, '') : null)
const int = (v: string) => Math.max(0, Math.round(Number(v.replace(',', '.')) || 0))
const txt = (v: string) => (v.trim() ? v.trim() : null)

async function submit() {
  errors.value = {}
  error.value = ''
  duplicateId.value = null
  if (!form.value.name.trim()) {
    errors.value.name = t('validation.missing')
    return
  }
  busy.value = true
  const f = form.value
  const body: Record<string, unknown> = {
    kind: f.kind,
    name: f.name.trim(),
    brand: txt(f.brand),
    code: txt(f.code),
    vehicles: txt(f.vehicles),
    sale_price: dec(f.sale_price),
    sale_currency: f.sale_price.trim() ? f.sale_currency || null : null,
    min_quantity: int(f.min_quantity),
    notes: txt(f.notes),
    public_visible: f.public_visible,
    frequency_mhz: electronic.value ? dec(f.frequency_mhz) : null,
    chip_type: electronic.value ? txt(f.chip_type) : null,
    fcc_id: electronic.value ? txt(f.fcc_id) : null,
  }
  if (session.seesPurchase) {
    body.purchase_price = dec(f.purchase_price)
    body.purchase_currency = f.purchase_price.trim() ? f.purchase_currency || null : null
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
      const it = await call(
        client.POST('/api/v1/workshops/{workshop_id}/inventory/items', {
          params: { path },
          body: { ...body, quantity: int(f.quantity), location_id: f.location_id } as Schemas['StockItemCreateIn'],
        }),
      )
      qc.invalidateQueries({ queryKey: ['items', session.wid] })
      qc.invalidateQueries({ queryKey: ['reorder', session.wid] })
      if (it.catalog === 'linked') toast.show(t('item.form.linked'))
      else if (it.catalog === 'proposed') toast.show(t('item.form.proposed'))
      router.replace({ name: 'item', params: { id: it.id } })
    }
  } catch (e) {
    errors.value = fieldErrors(e)
    if (e instanceof ApiError && e.code === 'inventory.duplicate') duplicateId.value = String(e.params.item_id)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
