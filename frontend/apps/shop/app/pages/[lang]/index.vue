<template>
  <div class="flex flex-col gap-8 md:gap-12">
    <section class="flex flex-col gap-4 md:max-w-3xl">
      <h1 class="m-0 text-[30px] leading-tight font-bold md:text-[42px]">{{ t('home.title') }}</h1>
      <p class="m-0 text-[18px] text-muted">{{ t('home.lead') }}</p>
      <KeySearch />
    </section>

    <section class="grid gap-4 md:grid-cols-2">
      <div class="flex flex-col gap-2 rounded-card border border-line bg-surface p-5">
        <h2 class="m-0 text-[20px] font-bold">{{ t('home.ownersTitle') }}</h2>
        <p class="m-0 text-muted">{{ t('home.ownersText') }}</p>
        <NuxtLink :to="path('/keys')" class="mt-1 font-semibold text-ink">{{ t('keys.all') }} →</NuxtLink>
      </div>
      <div class="flex flex-col gap-2 rounded-card bg-graphite p-5 text-on-graphite">
        <h2 class="m-0 text-[20px] font-bold">{{ t('home.shopsTitle') }}</h2>
        <p class="m-0 text-on-graphite-muted">{{ t('home.shopsText') }}</p>
        <ul class="m-0 flex flex-col gap-1.5 pl-0">
          <li v-for="p in t('home.shopsPoints').split('|')" :key="p" class="flex list-none items-center gap-2"><UIIcon name="check" :size="18" class="text-primary" />{{ p }}</li>
        </ul>
      </div>
    </section>

    <section v-if="keys?.length" class="flex flex-col gap-3">
      <h2 class="m-0 text-[20px] font-bold">{{ t('site.keys') }}</h2>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <KeyCard v-for="k in keys" :key="k.slug" :item="k" />
      </div>
    </section>

    <WaitlistForm source="home" />
  </div>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'

definePageMeta({ validate: (route) => isLang(route.params.lang) })
const { t, path, lang } = useLang()
const { data: keys } = await useAsyncData(`home-keys`, () => apiFetch<PublicKeyBrief[]>('/keys', { query: { limit: 6 } }).catch(() => []))

useSeoLinks('')
useSeoMeta({
  title: () => `KeyVerhaus — ${t('site.tagline')}`,
  description: () => t('home.lead'),
  ogTitle: () => `KeyVerhaus — ${t('site.tagline')}`,
  ogDescription: () => t('home.lead'),
  ogType: 'website',
})
useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: () => JSON.stringify({ '@context': 'https://schema.org', '@type': 'WebSite', name: 'KeyVerhaus', inLanguage: lang.value }),
    },
  ],
})
</script>
