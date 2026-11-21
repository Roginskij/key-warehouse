<template>
  <PageHeader :title="t('admin.workshops.title')" :subtitle="list.data.value ? t('admin.workshops.total', { n: list.data.value.total }) : undefined">
    <label class="flex h-12 items-center gap-2.5 rounded-control border-2 border-graphite-2 bg-graphite-2 px-3 text-on-graphite-muted md:max-w-md md:border-line-strong md:bg-surface md:text-muted">
      <UIIcon name="search" :size="22" />
      <input v-model="search" type="search" :placeholder="t('admin.workshops.search')" :aria-label="t('admin.workshops.search')" class="min-w-0 flex-1 bg-transparent text-[16px] text-on-graphite outline-none md:text-ink" />
    </label>
  </PageHeader>

  <div class="flex flex-col gap-2 p-3 md:p-0 md:pb-12">
    <p class="m-0 mb-1 text-[14px] text-muted">{{ t('admin.workshops.privacy') }}</p>
    <LoadError v-if="list.isError.value && !list.data.value" :error="list.error.value" @retry="list.refetch()" />
    <div v-else-if="list.isPending.value" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="list.data.value && !list.data.value.items.length" icon="home" :title="t('admin.workshops.none')" />
    <RouterLink
      v-for="w in list.data.value?.items"
      :key="w.id"
      :to="{ name: 'admin-workshop', params: { id: w.id } }"
      class="flex flex-col gap-1 rounded-[14px] border border-line bg-surface p-4 text-ink no-underline hover:border-line-strong md:flex-row md:items-center md:gap-4"
    >
      <span class="flex min-w-0 flex-1 flex-col">
        <b class="truncate">{{ w.name }}</b>
        <span class="text-[14px] text-muted">{{ country(w.country) }} · {{ t('admin.workshops.since', { date: dateTime(w.created_at) }) }}</span>
      </span>
      <span class="flex flex-wrap gap-x-4 gap-y-1 text-[14px] text-muted">
        <span>{{ t('admin.workshops.people', { n: w.members }) }}</span>
        <span>{{ t('admin.workshops.items', { n: w.items }) }}</span>
        <span>{{ w.last_activity ? t('admin.workshops.lastActivity', { date: dateTime(w.last_activity) }) : t('admin.workshops.noActivity') }}</span>
        <span v-if="w.public_listed" class="font-semibold text-ink">{{ t('admin.workshops.onSite') }}</span>
      </span>
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { UIEmpty, UIIcon } from '@kv/ui'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { dateTime } from '@/lib/format'

const { t, locale } = useI18n()
const search = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (q.value = v.trim()), 250)
})
const list = useQuery({
  queryKey: computed(() => ['admin-workshops', q.value]),
  queryFn: () => call(client.GET('/api/v1/admin/workshops', { params: { query: { q: q.value || undefined, limit: 100 } } })),
  placeholderData: keepPreviousData,
})
const country = (c: string) => new Intl.DisplayNames([locale.value], { type: 'region' }).of(c) ?? c
</script>
