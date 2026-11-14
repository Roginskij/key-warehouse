<template>
  <PageHeader :title="t('import.title')" :back="{ name: 'more' }" :back-label="t('common.back')">
    <div v-if="session.isOwner && step < 4" class="flex flex-col gap-2">
      <div class="grid grid-cols-3 gap-1.5" :aria-label="t('import.step', { n: step })">
        <span v-for="n in 3" :key="n" class="h-1.5 rounded-full" :class="n <= step ? 'bg-primary' : 'bg-graphite-2 md:bg-line-strong'" />
      </div>
      <span class="text-sm text-on-graphite-muted md:text-muted">{{ t('import.step', { n: step }) }}</span>
    </div>
  </PageHeader>

  <div class="flex flex-col gap-3 p-3 md:max-w-2xl md:p-0 md:pb-12">
    <UIEmpty v-if="!session.isOwner" icon="users" :title="t('import.ownerOnly')" />

    <template v-else-if="step === 1">
      <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
        <h2 class="m-0 text-xl font-bold">{{ t('import.pickTitle') }}</h2>
        <p class="m-0 text-muted">{{ t('import.pickText') }}</p>
        <label :class="buttonClass('primary', 'lg', true)" class="cursor-pointer">
          <UIIcon name="file" :size="20" />{{ busy ? t('import.reading') : t('import.pick') }}
          <input type="file" accept=".xlsx,.xlsm,.csv,.txt" class="sr-only" :disabled="busy" @change="pick" />
        </label>
        <p class="m-0 text-sm text-muted">{{ t('import.formats') }}</p>
      </section>
    </template>

    <template v-else-if="step === 2 && analysis">
      <h2 class="m-0 px-1 text-xl font-bold">{{ t('import.mapTitle') }}</h2>
      <p class="m-0 px-1 text-muted">{{ t('import.mapText') }}</p>
      <p class="m-0 flex items-center gap-2 px-1 text-[15px]"><UIIcon name="file" :size="20" />{{ file?.name }} · {{ t('import.rows', { n: num(analysis.rows_total) }) }}</p>
      <section class="flex flex-col divide-y divide-ground rounded-card border border-line bg-surface px-4">
        <div v-for="f in visibleFields" :key="f" class="grid grid-cols-[1.75rem_minmax(0,1fr)_minmax(0,11rem)] items-center gap-2 py-2.5">
          <span
            class="flex size-7 items-center justify-center rounded-full text-sm font-bold"
            :class="mapping[f] ? 'bg-primary-soft' : 'bg-ground text-faint'"
            aria-hidden="true"
          ><UIIcon v-if="mapping[f]" name="check" :size="16" :stroke="3" /><template v-else>–</template></span>
          <span class="text-[15px] font-semibold">{{ t(`import.fields.${f}`) }}</span>
          <UISelect v-model="mapping[f]" :label="t(`import.fields.${f}`)" :options="colOptions" class="[&>label]:sr-only" />
        </div>
      </section>
      <section class="grid gap-3 rounded-card border border-line bg-surface p-4 sm:grid-cols-3">
        <UISelect v-model="defaultKind" :label="t('import.defaultKind')" :options="kindOptions" />
        <UISelect v-model="currency" :label="t('import.currency')" :options="curOptions" />
        <UISelect v-model="locationId" :label="t('import.location')" :options="locOptions" />
      </section>
      <section v-if="firstRow" class="rounded-card border border-line bg-surface p-4">
        <span class="text-sm font-semibold text-muted">{{ t('import.firstRow') }}</span>
        <p class="m-0 mt-1 text-[16px] font-semibold">{{ firstRow }}</p>
      </section>
      <UIButton size="lg" block :loading="busy" :disabled="!mapping.name && !mapping.code" @click="run(true)">{{ t('import.check') }}</UIButton>
      <button type="button" class="self-center text-[15px] font-semibold underline" @click="restart">{{ t('import.otherFile') }}</button>
    </template>

    <template v-else-if="(step === 3 || step === 4) && report">
      <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
        <h2 class="m-0 text-xl font-bold">{{ step === 3 ? t('import.previewTitle') : t('import.doneTitle') }}</h2>
        <ul class="m-0 flex list-none flex-col gap-1.5 p-0 text-[16px]">
          <li><b>{{ num(report.created) }}</b> {{ t('import.created') }} · <b>{{ num(report.total_quantity) }}</b> {{ t('common.pcsShort') }}</li>
          <li v-if="report.linked_to_catalog">{{ t('import.linked', { n: report.linked_to_catalog }) }}</li>
          <li v-if="report.duplicates.length" class="text-muted">{{ t('import.duplicates', { n: report.duplicates.length }) }}</li>
          <li v-if="report.skipped_empty" class="text-muted">{{ t('import.empty', { n: report.skipped_empty }) }}</li>
        </ul>
        <div v-if="report.errors.length" class="rounded-control bg-warn-bg p-3 text-warn">
          <p class="m-0 font-semibold">{{ t('import.errors', { n: report.errors.length }) }}</p>
          <ul class="m-0 mt-1 pl-5 text-[15px]">
            <li v-for="e in report.errors.slice(0, 10)" :key="e.row">{{ t('import.row', { n: e.row }) }}: {{ e.reason }}</li>
          </ul>
        </div>
      </section>
      <template v-if="step === 3">
        <UIButton size="lg" block :loading="busy" :disabled="!report.created" @click="run(false)">{{ t('import.save', { n: report.created }) }}</UIButton>
        <button type="button" class="self-center text-[15px] font-semibold underline" @click="step = 2">{{ t('import.fixColumns') }}</button>
      </template>
      <RouterLink v-else :to="{ name: 'stock' }" :class="buttonClass('primary', 'lg', true)">{{ t('import.toStock') }}</RouterLink>
    </template>

    <p v-if="error" role="alert" class="m-0 rounded-control bg-danger-bg p-4 text-danger">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIEmpty, UIIcon, UISelect } from '@kv/ui'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/PageHeader.vue'
import { raw } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { num } from '@/lib/format'
import { useCurrencies, useLocationNames } from '@/lib/queries'
import { useSession } from '@/stores/session'

interface Analysis {
  headers: string[]
  rows_total: number
  sample: Record<string, string>[]
  suggested_mapping: Record<string, string>
  fields: string[]
}
interface Report {
  rows_total: number
  created: number
  skipped_empty: number
  duplicates: { row: number; code: string }[]
  errors: { row: number; reason: string }[]
  linked_to_catalog: number
  proposed_to_catalog: number
  total_quantity: number
  dry_run: boolean
}

const { t } = useI18n()
const session = useSession()
const qc = useQueryClient()
const { data: currencies } = useCurrencies()
const places = useLocationNames()

const step = ref<1 | 2 | 3 | 4>(1)
const file = ref<File | null>(null)
const analysis = ref<Analysis | null>(null)
const mapping = ref<Record<string, string>>({})
const defaultKind = ref('blank')
const currency = ref('')
const locationId = ref('')
const report = ref<Report | null>(null)
const error = ref('')
const busy = ref(false)
const base = `/api/v1/workshops/${session.wid}/inventory/import`

const FIELDS = ['name', 'code', 'brand', 'kind', 'quantity', 'sale_price', 'purchase_price', 'min_quantity', 'vehicles', 'location', 'notes', 'stale']
const visibleFields = computed(() => FIELDS.filter((f) => session.seesPurchase || f !== 'purchase_price'))
const colOptions = computed(() => [
  { value: '', label: t('import.notInFile') },
  ...(analysis.value?.headers ?? []).map((h) => ({ value: h, label: h })),
])
const KINDS = ['blank', 'car_key', 'remote', 'transponder', 'cylinder', 'key_shell', 'battery', 'other']
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
const curOptions = computed(() => [{ value: '', label: t('item.form.baseCurrency') }, ...(currencies.value ?? []).map((c) => ({ value: c.code, label: c.code }))])
const locOptions = computed(() => [{ value: '', label: t('locations.main') }, ...[...places.value].map(([value, label]) => ({ value, label }))])
const firstRow = computed(() => {
  const row = analysis.value?.sample[0]
  if (!row) return ''
  const v = (f: string) => (mapping.value[f] ? row[mapping.value[f]] : '')
  return [v('name') || v('code'), v('code') && v('name') ? v('code') : '', v('quantity') && `${v('quantity')} ${t('common.pcsShort')}`, v('sale_price')]
    .filter(Boolean)
    .join(' · ')
})

async function pick(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  file.value = f
  error.value = ''
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    analysis.value = (await (await raw(`${base}/analyze`, { method: 'POST', body: fd })).json()) as Analysis
    mapping.value = Object.fromEntries(FIELDS.map((f) => [f, analysis.value!.suggested_mapping[f] ?? '']))
    step.value = 2
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}

async function run(dryRun: boolean) {
  if (!file.value) return
  error.value = ''
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('mapping', JSON.stringify(Object.fromEntries(Object.entries(mapping.value).filter(([, v]) => v))))
    fd.append('default_kind', defaultKind.value)
    if (currency.value) fd.append('currency', currency.value)
    if (locationId.value) fd.append('location_id', locationId.value)
    fd.append('dry_run', String(dryRun))
    report.value = (await (await raw(base, { method: 'POST', body: fd })).json()) as Report
    step.value = dryRun ? 3 : 4
    if (!dryRun) {
      qc.invalidateQueries({ queryKey: ['items', session.wid] })
      qc.invalidateQueries({ queryKey: ['locations', session.wid] })
      qc.invalidateQueries({ queryKey: ['reorder', session.wid] })
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}

function restart() {
  step.value = 1
  file.value = null
  analysis.value = null
  report.value = null
}
</script>
