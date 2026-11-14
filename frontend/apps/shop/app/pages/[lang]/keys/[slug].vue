<template>
  <article v-if="key" class="flex flex-col gap-6">
    <nav :aria-label="t('site.keys')" class="text-[14px] text-muted">
      <NuxtLink :to="path()" class="text-muted">KeyVerhaus</NuxtLink> ›
      <NuxtLink :to="path('/keys')" class="text-muted">{{ t('site.keys') }}</NuxtLink> ›
      <span>{{ key.name }}</span>
    </nav>

    <div class="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,20rem)]">
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-[14px] font-semibold text-muted">{{ t(`kinds.${key.kind}`) }}</span>
          <h1 class="m-0 text-[28px] leading-tight font-bold md:text-[34px]">{{ key.name }}</h1>
        </div>
        <p v-if="key.description" class="m-0 text-[17px] whitespace-pre-line">{{ key.description }}</p>

        <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('key.codes') }}</h2>
          <p class="m-0 text-[14px] text-muted">{{ t('key.codesHint') }}</p>
          <ul class="m-0 flex flex-wrap gap-2 p-0">
            <li v-for="c in key.codes" :key="c.brand + c.code" class="list-none rounded-control bg-ground px-3 py-1.5"><b>{{ c.code }}</b> <span class="text-muted">{{ c.brand }}</span></li>
          </ul>
          <dl v-if="key.frequency_mhz || key.chip_type" class="m-0 mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[15px]">
            <template v-if="key.frequency_mhz"><dt class="text-muted">{{ t('key.frequency') }}</dt><dd class="m-0">{{ key.frequency_mhz }} MHz</dd></template>
            <template v-if="key.chip_type"><dt class="text-muted">{{ t('key.chip') }}</dt><dd class="m-0">{{ key.chip_type }}</dd></template>
          </dl>
        </section>

        <section v-if="key.vehicles.length" class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('key.vehicles') }}</h2>
          <ul class="m-0 flex flex-col gap-1 p-0">
            <li v-for="(v, i) in key.vehicles" :key="i" class="list-none">
              <b>{{ v.make }} {{ v.model }}</b> <span v-if="v.year_from || v.year_to" class="text-muted">{{ v.year_from ?? '…' }}–{{ v.year_to ?? '…' }}</span>
            </li>
          </ul>
        </section>

        <section v-if="key.locks.length" class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 text-[17px] font-bold">{{ t('key.locks') }}</h2>
          <ul class="m-0 flex flex-col gap-1 p-0">
            <li v-for="(l, i) in key.locks" :key="i" class="list-none"><b>{{ l.make }} {{ l.model }}</b> <span v-if="l.profile" class="text-muted">· {{ l.profile }}</span></li>
          </ul>
        </section>

        <section v-if="key.can_be_replaced_by.length || key.can_replace.length" class="flex flex-col gap-3">
          <div v-if="key.can_be_replaced_by.length" class="flex flex-col gap-2">
            <h2 class="m-0 text-[17px] font-bold">{{ t('key.replacedBy') }}</h2>
            <div class="grid gap-2 sm:grid-cols-2"><KeyCard v-for="k in key.can_be_replaced_by" :key="k.slug" :item="k" /></div>
          </div>
          <div v-if="key.can_replace.length" class="flex flex-col gap-2">
            <h2 class="m-0 text-[17px] font-bold">{{ t('key.replaces') }}</h2>
            <div class="grid gap-2 sm:grid-cols-2"><KeyCard v-for="k in key.can_replace" :key="k.slug" :item="k" /></div>
          </div>
        </section>
      </div>

      <aside class="flex flex-col gap-3">
        <figure v-for="(img, i) in key.images" :key="img.url" class="m-0" :class="i > 0 ? 'hidden md:block' : ''">
          <img :src="img.url" :alt="key.name" :width="img.width" :height="img.height" :loading="i ? 'lazy' : 'eager'" class="h-auto w-full rounded-card border border-line bg-surface object-contain" />
        </figure>
      </aside>
    </div>

    <!-- Find a workshop -->
    <section id="where" class="flex flex-col gap-3">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <h2 class="m-0 text-[22px] font-bold">{{ t('key.find') }}</h2>
        <UISelect v-if="cities?.length" v-model="city" class="min-w-56" :label="t('key.city')" :options="cityOptions" />
      </div>
      <div v-if="shown.length" class="grid gap-3 md:grid-cols-2">
        <WorkshopCard v-for="w in shown" :key="w.id" :w="w" :key-slug="key.slug" show-stock />
      </div>
      <div v-else class="flex flex-col gap-1 rounded-card border border-line bg-surface p-5">
        <p class="m-0 font-bold">{{ t('key.none') }}</p>
        <p class="m-0 text-muted">{{ t('key.noneHint') }}</p>
      </div>
    </section>

    <WaitlistForm :source="`key:${key.slug}`" />
  </article>
</template>

<script setup lang="ts">
import { UISelect } from '@kv/ui'

definePageMeta({ validate: (route) => isLang(route.params.lang) })
const { t, path, lang } = useLang()
const route = useRoute()
const slug = computed(() => String(route.params.slug))

const { data } = await useAsyncData(`key-${slug.value}`, () =>
  apiFetch<{ redirect_to: string | null; key: PublicKey | null }>(`/keys/${encodeURIComponent(slug.value)}`).catch((e) => {
    if (e?.statusCode === 404 || e?.response?.status === 404) return null
    throw e
  }),
)
// Merged duplicates keep their old links working: permanent redirect to the main page.
if (data.value?.redirect_to) await navigateTo(path(`/keys/${data.value.redirect_to}`), { redirectCode: 301 })
if (!data.value?.key) throw createError({ statusCode: 404, statusMessage: 'Key not found', fatal: true })
const key = computed(() => data.value!.key!)

const { data: cities } = await useAsyncData(`cities`, () => apiFetch<string[]>('/cities').catch(() => []))
const { data: workshops } = await useAsyncData(`key-ws-${slug.value}`, () => apiFetch<PublicWorkshop[]>(`/keys/${encodeURIComponent(slug.value)}/workshops`).catch(() => []))
const city = ref(typeof route.query.city === 'string' ? route.query.city : '')
const cityOptions = computed(() => [{ value: '', label: t('key.allCities') }, ...(cities.value ?? []).map((c) => ({ value: c, label: c }))])
const shown = computed(() => (workshops.value ?? []).filter((w) => !city.value || (w.city ?? '').toLowerCase() === city.value.toLowerCase()))

// --- SEO
const absolute = useAbsoluteUrl()
const codes = computed(() => key.value.codes.map((c) => c.code).filter((c, i, a) => a.indexOf(c) === i).join(', '))
const description = computed(() => (key.value.description ?? t('key.describe', { name: key.value.name, codes: codes.value })).slice(0, 160))
const mainImage = computed(() => (key.value.images[0] ? absolute(key.value.images[0].url) : undefined))
useSeoLinks(() => `/keys/${key.value.slug}`)
useSeoMeta({
  title: () => `${key.value.name} (${codes.value}) — KeyVerhaus`,
  description,
  ogTitle: () => `${key.value.name} (${codes.value})`,
  ogDescription: description,
  ogType: 'website',
  ogImage: mainImage,
})
const { siteUrl } = useRuntimeConfig().public
useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: () =>
        JSON.stringify([
          {
            '@context': 'https://schema.org',
            '@type': 'Product',
            name: key.value.name,
            description: description.value,
            category: t(`kinds.${key.value.kind}`),
            image: key.value.images.map((i) => absolute(i.url)),
            // Codes are compatibility references, not a claim of the manufacturer's product.
            additionalProperty: key.value.codes.map((c) => ({ '@type': 'PropertyValue', name: c.brand, value: c.code })),
            isAccessoryOrSparePartFor: key.value.vehicles.map((v) => ({ '@type': 'Car', brand: v.make, model: v.model })),
          },
          {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement: [
              { '@type': 'ListItem', position: 1, name: 'KeyVerhaus', item: `${siteUrl}/${lang.value}` },
              { '@type': 'ListItem', position: 2, name: t('site.keys'), item: `${siteUrl}/${lang.value}/keys` },
              { '@type': 'ListItem', position: 3, name: key.value.name, item: `${siteUrl}/${lang.value}/keys/${key.value.slug}` },
            ],
          },
        ]),
    },
  ],
})
</script>
