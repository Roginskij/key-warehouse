<template>
  <div class="flex flex-col gap-5">
    <div class="flex flex-col gap-2">
      <h1 class="m-0 text-[28px] font-bold">{{ t('keys.title') }}</h1>
      <p class="m-0 text-muted">{{ t('keys.lead') }}</p>
    </div>
    <KeySearch :initial="q" />
    <p v-if="q && items" class="m-0 text-[14px] text-muted">{{ t('keys.results', { n: items.length }) }}</p>
    <div v-if="items?.length" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <KeyCard v-for="k in items" :key="k.slug" :item="k" />
    </div>
    <div v-else class="flex flex-col items-center gap-2 rounded-card border border-line bg-surface px-6 py-10 text-center">
      <p class="m-0 text-lg font-bold">{{ t('keys.empty') }}</p>
      <p class="m-0 text-muted">{{ t('keys.emptyHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ validate: (route) => isLang(route.params.lang) })
const { t } = useLang()
const route = useRoute()
const q = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const { data: items } = await useAsyncData(
  () => `keys-${q.value}`,
  () => apiFetch<PublicKeyBrief[]>('/keys', { query: { q: q.value || undefined, limit: 60 } }),
  { watch: [q] },
)

useSeoLinks('/keys')
useSeoMeta({
  title: () => `${t('keys.title')}${q.value ? `: ${q.value}` : ''} — KeyVerhaus`,
  description: () => t('keys.lead'),
  // Search result pages are not indexed; the list itself and key pages are.
  robots: () => (q.value ? 'noindex, follow' : 'index, follow'),
})
</script>
