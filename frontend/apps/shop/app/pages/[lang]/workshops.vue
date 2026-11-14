<template>
  <div class="flex flex-col gap-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div class="flex flex-col gap-2">
        <h1 class="m-0 text-[28px] font-bold">{{ t('workshops.title') }}{{ city ? ` — ${city}` : '' }}</h1>
        <p class="m-0 text-muted">{{ t('workshops.lead') }}</p>
      </div>
      <UISelect v-if="cities?.length" v-model="city" class="min-w-56" :label="t('key.city')" :options="cityOptions" />
    </div>
    <div v-if="workshops?.length" class="grid gap-3 md:grid-cols-2">
      <WorkshopCard v-for="w in workshops" :key="w.id" :w="w" />
    </div>
    <div v-else class="flex flex-col gap-1 rounded-card border border-line bg-surface p-5">
      <p class="m-0 font-bold">{{ t('workshops.empty') }}</p>
      <p class="m-0 text-muted">{{ t('key.noneHint') }}</p>
    </div>
    <WaitlistForm source="workshops" />
  </div>
</template>

<script setup lang="ts">
import { UISelect } from '@kv/ui'

definePageMeta({ validate: (route) => isLang(route.params.lang) })
const { t } = useLang()
const route = useRoute()
const router = useRouter()
const city = computed({
  get: () => (typeof route.query.city === 'string' ? route.query.city : ''),
  set: (v: string) => router.replace({ query: v ? { city: v } : {} }),
})
const { data: cities } = await useAsyncData('cities', () => apiFetch<string[]>('/cities').catch(() => []))
const { data: workshops } = await useAsyncData(
  () => `workshops-${city.value}`,
  () => apiFetch<PublicWorkshop[]>('/workshops', { query: { city: city.value || undefined } }),
  { watch: [city] },
)
const cityOptions = computed(() => [{ value: '', label: t('key.allCities') }, ...(cities.value ?? []).map((c) => ({ value: c, label: c }))])

useSeoLinks(() => '/workshops' + (city.value ? `?city=${encodeURIComponent(city.value)}` : ''))
useSeoMeta({
  title: () => `${t('workshops.title')}${city.value ? ` — ${city.value}` : ''} — KeyVerhaus`,
  description: () => t('workshops.describe'),
})
</script>
