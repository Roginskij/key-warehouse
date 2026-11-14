<template>
  <PageHeader :title="t('publicProfile.title')" :subtitle="t('publicProfile.subtitle')" :back="{ name: 'more' }" :back-label="t('common.back')" />
  <div class="grid grid-cols-1 gap-3 p-3 md:gap-5 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
    <UIEmpty v-if="!session.isOwner" icon="users" :title="t('publicProfile.ownerOnly')" />
    <LoadError v-else-if="profile.isError.value && !profile.data.value" :error="profile.error.value" @retry="profile.refetch()" />
    <template v-else-if="profile.data.value">
      <form class="flex flex-col gap-3 md:gap-4" novalidate @submit.prevent="save">
        <!-- Consent: nothing is public until this is on -->
        <section class="flex flex-col gap-3 rounded-card border-2 p-4" :class="form.public_listed ? 'border-ink bg-surface' : 'border-line bg-surface'">
          <label class="flex items-start gap-3">
            <input v-model="form.public_listed" type="checkbox" class="mt-0.5 size-6 shrink-0 accent-ink" />
            <span class="flex flex-col gap-1">
              <span class="text-[17px] font-bold">{{ t('publicProfile.listed') }}</span>
              <span class="text-[14px] text-muted">{{ t('publicProfile.listedHint') }}</span>
            </span>
          </label>
        </section>

        <section class="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-2">
          <h2 class="m-0 text-[17px] font-bold sm:col-span-2">{{ t('publicProfile.where') }}</h2>
          <UIField v-model="form.public_city" :label="t('publicProfile.city')" :error="errors.public_city" />
          <UIField v-model="form.public_address" :label="t('publicProfile.address')" />
          <UIField v-model="form.public_hours" class="sm:col-span-2" :label="t('publicProfile.hours')" :placeholder="t('publicProfile.hoursExample')" />
        </section>

        <section class="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-3">
          <h2 class="m-0 text-[17px] font-bold sm:col-span-3">{{ t('publicProfile.contacts') }}</h2>
          <UIField v-model="form.public_phone" :label="t('publicProfile.phone')" type="tel" inputmode="tel" placeholder="+380…" :error="errors.public_phone" />
          <UIField v-model="form.public_viber" label="Viber" type="tel" inputmode="tel" />
          <UIField v-model="form.public_telegram" label="Telegram" placeholder="@name" />
        </section>

        <section class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4">
          <UISelect v-model="form.price_display" :label="t('publicProfile.prices')" :options="priceOptions" />
          <label class="flex flex-col gap-1.5">
            <span class="text-[15px] font-semibold">{{ t('publicProfile.about') }}</span>
            <textarea v-model="form.public_about" rows="3" maxlength="500" class="rounded-control border-2 border-line-strong p-3 text-[16px] outline-none focus:border-ink" />
          </label>
        </section>

        <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('publicProfile.verification') }}</h2>
          <p class="m-0 text-[14px] text-muted">{{ t('publicProfile.verificationHint') }}</p>
          <UIField v-model="form.tax_id" :label="t('publicProfile.taxId')" />
          <p class="m-0 text-[15px]">
            {{ t('publicProfile.status') }}: <b>{{ t(`publicProfile.statuses.${profile.data.value.verification_status}`) }}</b>
          </p>
        </section>

        <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
        <UIButton type="submit" size="lg" block :loading="busy" class="md:w-auto md:self-start">{{ t('common.save') }}</UIButton>
      </form>

      <aside class="flex flex-col gap-3 self-start">
        <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('publicProfile.stats') }}</h2>
          <p class="m-0 text-[14px] text-muted">{{ t('publicProfile.statsHint') }}</p>
          <div v-for="c in CHANNELS" :key="c" class="flex justify-between border-b border-ground py-1.5 last:border-0">
            <span>{{ t(`publicProfile.channels.${c}`) }}</span><b>{{ profile.data.value.clicks_30d[c] ?? 0 }}</b>
          </div>
        </section>
        <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('publicProfile.items', { n: profile.data.value.public_items }) }}</h2>
          <p class="m-0 text-[14px] text-muted">{{ t('publicProfile.itemsHint') }}</p>
        </section>
      </aside>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIEmpty, UIField, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const CHANNELS = ['phone', 'viber', 'telegram', 'route'] as const

const key = computed(() => ['profile', session.wid])
const profile = useQuery({
  queryKey: key,
  queryFn: () => call(client.GET('/api/v1/workshops/{workshop_id}/profile', { params: { path: { workshop_id: session.wid } } })),
  enabled: computed(() => session.isOwner && !!session.wid),
})

const empty = () => ({
  public_listed: false,
  public_city: '',
  public_address: '',
  public_hours: '',
  public_phone: '',
  public_viber: '',
  public_telegram: '',
  public_about: '',
  price_display: 'ask' as Schemas['PriceDisplay'],
  tax_id: '',
})
const form = ref(empty())
watch(
  () => profile.data.value,
  (p) => {
    if (!p) return
    const f = empty()
    for (const k of Object.keys(f) as (keyof typeof f)[]) {
      const v = p[k as keyof typeof p]
      if (v !== null && v !== undefined) (f as Record<string, unknown>)[k] = v
    }
    form.value = f
  },
  { immediate: true },
)

const priceOptions = computed(() => (['ask', 'from', 'exact'] as const).map((v) => ({ value: v, label: t(`publicProfile.price.${v}`) })))

const errors = ref<Record<string, string>>({})
const error = ref('')
const busy = ref(false)

async function save() {
  errors.value = {}
  error.value = ''
  const f = form.value
  // A listed workshop must be findable and reachable.
  if (f.public_listed) {
    if (!f.public_city.trim()) errors.value.public_city = t('validation.missing')
    if (!f.public_phone.trim() && !f.public_viber.trim() && !f.public_telegram.trim()) errors.value.public_phone = t('publicProfile.needContact')
    if (Object.keys(errors.value).length) return
  }
  busy.value = true
  try {
    const out = await call(
      client.PUT('/api/v1/workshops/{workshop_id}/profile', {
        params: { path: { workshop_id: session.wid } },
        body: { ...f },
      }),
    )
    qc.setQueryData(key.value, out)
    toast.show(t('common.saved'))
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
