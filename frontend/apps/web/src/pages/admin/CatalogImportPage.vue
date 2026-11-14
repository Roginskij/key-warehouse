<template>
  <PageHeader :title="t('admin.import.title')" :subtitle="t('admin.import.subtitle')" />
  <div class="grid gap-4 p-3 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
    <div class="flex flex-col gap-4">
      <section class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4">
        <p class="m-0 text-[15px] text-muted">{{ t('admin.import.format') }}</p>
        <a href="/catalog-import-template.csv" download class="self-start text-[15px] font-semibold text-ink">{{ t('admin.import.template') }}</a>
        <label :class="buttonClass('outline', 'md')" class="cursor-pointer self-start">
          <UIIcon name="file" :size="18" />{{ file ? file.name : t('import.pick') }}
          <input type="file" accept=".xlsx,.xlsm,.csv" class="sr-only" @change="pick" />
        </label>
        <UIField v-model="label" :label="t('admin.import.label')" :placeholder="t('admin.import.labelPlaceholder')" :hint="t('admin.import.labelHint')" />
        <UISelect v-model="kind" :label="t('admin.import.defaultKind')" :options="kindOptions" />
        <UIButton size="lg" :loading="busy" :disabled="!file || !label.trim()" @click="run(true)">{{ t('import.check') }}</UIButton>
      </section>
      <p v-if="error" role="alert" class="m-0 rounded-control bg-danger-bg p-4 text-danger">{{ error }}</p>

      <section v-if="report" class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ report.dry_run ? t('import.previewTitle') : t('admin.import.doneTitle') }}</h2>
        <ul class="m-0 flex list-none flex-col gap-1 p-0 text-[15px]">
          <li>{{ t('admin.import.created', { n: num(report.created_items) }) }}</li>
          <li>{{ t('admin.import.updated', { n: num(report.updated_items), codes: num(report.codes_added) }) }}</li>
          <li class="text-muted">{{ t('admin.import.unchanged', { n: num(report.unchanged) }) }}</li>
          <li v-if="report.new_brands.length">{{ t('admin.import.newBrands', { list: report.new_brands.join(', ') }) }}</li>
        </ul>
        <div v-if="report.conflicts.length" class="rounded-control bg-warn-bg p-3 text-[15px] text-warn">
          <p class="m-0 font-semibold">{{ t('admin.import.conflicts', { n: report.conflicts.length }) }}</p>
          <p v-for="c in report.conflicts.slice(0, 10)" :key="c.row" class="m-0">
            {{ t('import.row', { n: c.row }) }}:
            <RouterLink v-for="(id, i) in c.item_ids" :key="id" :to="{ name: 'admin-item', params: { id } }" class="font-semibold text-warn">{{ i ? ', ' : '' }}#{{ i + 1 }}</RouterLink>
          </p>
        </div>
        <div v-if="report.errors.length" class="rounded-control bg-danger-bg p-3 text-[15px] text-danger">
          <p class="m-0 font-semibold">{{ t('import.errors', { n: report.errors.length }) }}</p>
          <p v-for="e in report.errors.slice(0, 10)" :key="e.row" class="m-0">{{ t('import.row', { n: e.row }) }}: {{ e.reason }}</p>
        </div>
        <UIButton v-if="report.dry_run" size="lg" :loading="busy" :disabled="!report.created_items && !report.codes_added" @click="run(false)">
          {{ t('admin.import.apply') }}
        </UIButton>
      </section>
    </div>

    <section class="flex flex-col gap-2 self-start rounded-card border border-line bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('admin.import.history') }}</h2>
      <p v-if="!imports.data.value?.length" class="m-0 text-muted">{{ t('admin.import.noHistory') }}</p>
      <div v-for="i in imports.data.value" :key="i.id" class="flex items-center gap-3 border-t border-ground py-2 first:border-0">
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate font-semibold">{{ i.source_label }}</span>
          <span class="truncate text-[13px] text-muted">{{ i.filename }} · {{ dateTime(i.created_at) }} · {{ t('admin.import.stat', { created: i.stats.created_items ?? 0, codes: i.stats.codes_added ?? 0 }) }}</span>
        </span>
        <span v-if="i.reverted_at" class="text-[13px] font-semibold text-muted">{{ t('admin.import.revertedLabel') }}</span>
        <UIButton v-else size="sm" variant="danger" @click="revert(i.id)">{{ t('admin.import.revert') }}</UIButton>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/PageHeader.vue'
import { KINDS } from '@/lib/admin'
import { call, client, raw } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { dateTime, num } from '@/lib/format'
import { useToast } from '@/stores/toast'

interface Report {
  rows_total: number
  created_items: number
  updated_items: number
  codes_added: number
  unchanged: number
  skipped_empty: number
  new_brands: string[]
  conflicts: { row: number; item_ids: string[] }[]
  errors: { row: number; reason: string }[]
  import_id: string | null
  dry_run: boolean
}

const { t } = useI18n()
const toast = useToast()
const qc = useQueryClient()
const file = ref<File | null>(null)
const label = ref('')
const kind = ref('')
const report = ref<Report | null>(null)
const busy = ref(false)
const error = ref('')
const kindOptions = computed(() => [{ value: '', label: t('admin.import.kindFromFile') }, ...KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) }))])

const imports = useQuery({ queryKey: ['admin-imports'], queryFn: () => call(client.GET('/api/v1/admin/catalog/imports')) })

function pick(e: Event) {
  file.value = (e.target as HTMLInputElement).files?.[0] ?? null
  report.value = null
}
async function run(dryRun: boolean) {
  if (!file.value || !label.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('source_label', label.value.trim())
    if (kind.value) fd.append('default_kind', kind.value)
    fd.append('dry_run', String(dryRun))
    report.value = (await (await raw('/api/v1/admin/catalog/import', { method: 'POST', body: fd })).json()) as Report
    if (!dryRun) {
      qc.invalidateQueries({ queryKey: ['admin-imports'] })
      qc.invalidateQueries({ queryKey: ['admin-catalog'] })
      toast.show(t('admin.import.saved'))
    }
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
async function revert(id: string) {
  try {
    await call(client.DELETE('/api/v1/admin/catalog/imports/{import_id}', { params: { path: { import_id: id } } }))
    qc.invalidateQueries({ queryKey: ['admin-imports'] })
    qc.invalidateQueries({ queryKey: ['admin-catalog'] })
    toast.show(t('admin.import.reverted'))
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
