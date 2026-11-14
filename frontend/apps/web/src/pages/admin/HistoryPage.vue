<template>
  <PageHeader :title="t('admin.history.title')" :subtitle="t('admin.history.subtitle')" />
  <div class="flex flex-col gap-2 p-3 md:p-0 md:pb-12">
    <LoadError v-if="isError && !data" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!data?.length" icon="file" :title="t('admin.history.empty')" :text="t('admin.history.emptyText')" />
    <section v-else class="rounded-card border border-line bg-surface">
      <div v-for="h in data" :key="h.id" class="flex flex-col gap-0.5 border-b border-ground px-4 py-2.5 last:border-0 md:flex-row md:items-baseline md:gap-4">
        <span class="shrink-0 text-[13px] text-muted md:w-32">{{ dateTime(h.created_at) }}</span>
        <span class="shrink-0 font-semibold md:w-56">{{ t(`admin.actions.${h.action.replace('.', '_')}`) }}</span>
        <RouterLink v-if="h.entity_type === 'item' && h.entity_id" :to="{ name: 'admin-item', params: { id: h.entity_id } }" class="min-w-0 truncate text-[14px] text-ink">
          {{ summary(h.data) || t('admin.item.open') }}
        </RouterLink>
        <span v-else class="min-w-0 truncate text-[14px] text-muted">{{ summary(h.data) }}</span>
      </div>
    </section>
    <button v-if="data && data.length >= limit" type="button" :class="buttonClass('outline', 'md')" class="self-center" :disabled="isFetching" @click="limit += 100">
      {{ t('admin.catalog.more') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIEmpty } from '@kv/ui'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { dateTime } from '@/lib/format'

const { t } = useI18n()
const limit = ref(100)
const { data, isFetching, isPending, isError, error, refetch } = useQuery({
  queryKey: computed(() => ['admin-audit', limit.value]),
  queryFn: () => call(client.GET('/api/v1/admin/catalog/audit', { params: { query: { limit: limit.value } } })),
  placeholderData: keepPreviousData,
})
const summary = (d: Record<string, unknown>) =>
  Object.entries(d)
    .filter(([, v]) => v !== null && typeof v !== 'object')
    .map(([k, v]) => `${k}: ${v}`)
    .join(' · ')
</script>
