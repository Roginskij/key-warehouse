<template>
  <PageHeader :title="t('admin.catalog.title')" :subtitle="data ? t('admin.catalog.total', { n: num(data.total) }) : undefined">
    <template #actions>
      <RouterLink v-if="session.can('catalog.edit')" :to="{ name: 'admin-item-new' }" :class="buttonClass('primary', 'md')">
        <UIIcon name="plus" :size="18" :stroke="2.6" />{{ t('admin.catalog.new') }}
      </RouterLink>
    </template>
    <div class="flex flex-wrap items-center gap-2">
      <label class="flex h-12 min-w-56 flex-1 items-center gap-2.5 rounded-control border-2 border-graphite-2 bg-graphite-2 px-3 text-on-graphite-muted md:max-w-md md:border-line-strong md:bg-surface md:text-muted">
        <UIIcon name="search" :size="22" />
        <input v-model="search" type="search" :placeholder="t('admin.catalog.search')" :aria-label="t('admin.catalog.search')" class="min-w-0 flex-1 bg-transparent text-[16px] text-on-graphite outline-none md:text-ink" />
      </label>
      <select v-model="kind" :aria-label="t('item.form.kind')" class="h-12 rounded-control border-2 border-graphite-2 bg-graphite-2 px-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink">
        <option value="">{{ t('admin.catalog.allKinds') }}</option>
        <option v-for="k in KINDS" :key="k" :value="k">{{ t(`kinds.${k}`) }}</option>
      </select>
      <select v-model="status" :aria-label="t('admin.catalog.status')" class="h-12 rounded-control border-2 border-graphite-2 bg-graphite-2 px-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink">
        <option v-for="s in ['active', 'archived', 'merged']" :key="s" :value="s">{{ t(`admin.status.${s}`) }}</option>
      </select>
    </div>
  </PageHeader>

  <div class="flex flex-col gap-2 p-3 md:p-0 md:pb-12">
    <LoadError v-if="isError && !data" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!items.length" icon="key" :title="t('admin.catalog.empty')" :text="t('admin.catalog.emptyText')" />
    <ul v-else class="m-0 flex list-none flex-col gap-2 p-0">
      <li v-for="i in items" :key="i.id">
        <RouterLink :to="{ name: 'admin-item', params: { id: i.id } }" class="flex flex-col gap-2 rounded-[14px] border border-line bg-surface p-4 text-ink no-underline hover:border-line-strong md:flex-row md:items-center">
          <span class="flex min-w-0 flex-col gap-0.5 md:w-72 md:shrink-0">
            <span class="truncate font-semibold">{{ i.name }}</span>
            <span class="text-[14px] text-muted">{{ t(`kinds.${i.kind}`) }} · {{ t(`admin.source.${i.source_type}`) }}</span>
          </span>
          <span class="flex flex-wrap gap-1.5">
            <span v-for="c in i.codes" :key="c.id" class="rounded-md bg-ground px-2 py-0.5 text-[14px] font-semibold">
              {{ c.brand }} {{ c.code }}<span v-if="c.confirmations" class="ml-1 text-muted">· {{ c.confirmations }}</span>
            </span>
            <span v-if="!i.codes.length" class="text-[14px] text-muted">{{ t('admin.catalog.noCodes') }}</span>
          </span>
          <UIIcon name="chevron" :size="20" class="ml-auto hidden shrink-0 text-faint md:block" />
        </RouterLink>
      </li>
    </ul>
    <button
      v-if="data && items.length < data.total"
      type="button"
      :class="buttonClass('outline', 'md')"
      class="self-center"
      :disabled="isFetching"
      @click="limit += 50"
    >{{ t('admin.catalog.more') }}</button>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIEmpty, UIIcon } from '@kv/ui'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { KINDS } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { num } from '@/lib/format'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const session = useSession()

const search = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    q.value = v.trim()
    limit.value = 50
  }, 250)
})
const kind = ref('')
const status = ref<'active' | 'archived' | 'merged'>('active')
const limit = ref(50)

const { data, isPending, isError, error, isFetching, refetch } = useQuery({
  queryKey: computed(() => ['admin-catalog', q.value, kind.value, status.value, limit.value]),
  queryFn: () =>
    call(
      client.GET('/api/v1/admin/catalog/items', {
        params: { query: { q: q.value || undefined, kind: (kind.value || undefined) as never, status: [status.value], limit: limit.value } },
      }),
    ),
  placeholderData: keepPreviousData,
})
const items = computed(() => data.value?.items ?? [])
</script>
