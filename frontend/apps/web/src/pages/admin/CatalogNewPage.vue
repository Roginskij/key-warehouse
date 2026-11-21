<template>
  <PageHeader :title="t('admin.catalog.new')" :back="{ name: 'admin-catalog' }" :back-label="t('admin.nav.catalog')" />
  <form class="flex flex-col gap-4 p-3 md:max-w-2xl md:p-0 md:pb-12" novalidate @submit.prevent="submit">
    <section class="grid gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
      <UISelect v-model="form.kind" :label="t('item.form.kind')" :options="kindOptions" />
      <UIField v-model="form.name" class="sm:col-span-2" :label="t('item.form.name')" :placeholder="t('item.form.namePlaceholder')" :error="errors.name" />
      <div class="sm:col-span-2"><CodeRows v-model="codes" /></div>
      <label class="flex flex-col gap-1.5 sm:col-span-2">
        <span class="text-[15px] font-semibold">{{ t('admin.item.description') }}</span>
        <textarea v-model="form.description" rows="3" class="rounded-control border-2 border-line-strong p-3 text-[16px] outline-none focus:border-ink" />
      </label>
      <template v-if="electronic">
        <UIField v-model="form.frequency_mhz" :label="t('item.form.frequency')" inputmode="decimal" :decimals="3" />
        <UIField v-model="form.chip_type" :label="t('item.form.chip')" />
        <UIField v-model="form.fcc_id" label="FCC ID" />
      </template>
    </section>
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">
      {{ error }}
      <RouterLink v-if="takenId" :to="{ name: 'admin-item', params: { id: takenId } }" class="ml-1 font-bold text-danger">{{ t('item.form.openExisting') }}</RouterLink>
    </div>
    <UIButton type="submit" size="lg" :loading="busy" class="md:self-start">{{ t('common.save') }}</UIButton>
  </form>
</template>

<script setup lang="ts">
import { ApiError } from '@kv/api'
import { UIButton, UIField, UISelect } from '@kv/ui'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import CodeRows from '@/components/admin/CodeRows.vue'
import PageHeader from '@/components/PageHeader.vue'
import { KINDS } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'

const { t } = useI18n()
const router = useRouter()
const qc = useQueryClient()

const form = ref({ kind: 'blank', name: '', description: '', frequency_mhz: '', chip_type: '', fcc_id: '' })
const codes = ref([{ brand: '', code: '' }])
const errors = ref<Record<string, string>>({})
const error = ref('')
const takenId = ref<string | null>(null)
const busy = ref(false)
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
const electronic = computed(() => ['car_key', 'remote', 'transponder'].includes(form.value.kind))
const txt = (v: string) => (v.trim() ? v.trim() : null)

async function submit() {
  errors.value = {}
  error.value = ''
  takenId.value = null
  busy.value = true
  try {
    const it = await call(
      client.POST('/api/v1/admin/catalog/items', {
        body: {
          kind: form.value.kind as never,
          name: form.value.name.trim(),
          description: txt(form.value.description),
          frequency_mhz: electronic.value ? txt(form.value.frequency_mhz.replace(',', '.')) : null,
          chip_type: electronic.value ? txt(form.value.chip_type) : null,
          fcc_id: electronic.value ? txt(form.value.fcc_id) : null,
          codes: codes.value.filter((c) => c.brand && c.code.trim()),
          attributes: {},
        },
      }),
    )
    qc.invalidateQueries({ queryKey: ['admin-catalog'] })
    router.replace({ name: 'admin-item', params: { id: it.id } })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (e instanceof ApiError && e.code === 'catalog.code_taken') takenId.value = String(e.params.item_id)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
