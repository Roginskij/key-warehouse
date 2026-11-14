<template>
  <PageHeader :title="t('admin.waitlist.title')" :subtitle="list.data.value ? t('admin.waitlist.total', { n: list.data.value.total }) : undefined" />
  <div class="flex flex-col gap-4 p-3 md:p-0 md:pb-12">
    <LoadError v-if="list.isError.value && !list.data.value" :error="list.error.value" @retry="list.refetch()" />
    <div v-else-if="list.isPending.value" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="list.data.value && !list.data.value.total" icon="users" :title="t('admin.waitlist.none')" :text="t('admin.waitlist.noneHint')" />
    <template v-else-if="list.data.value">
      <section class="grid gap-3 sm:grid-cols-2">
        <div class="rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 mb-2 text-[16px] font-bold">{{ t('admin.waitlist.byRole') }}</h2>
          <dl class="m-0 grid grid-cols-[1fr_auto] gap-y-1.5 text-[15px]">
            <template v-for="(n, r) in list.data.value.by_role" :key="r">
              <dt>{{ t(`admin.waitlist.roles.${r}`) }}</dt><dd class="m-0 text-right font-semibold tabular-nums">{{ n }}</dd>
            </template>
          </dl>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <h2 class="m-0 mb-2 text-[16px] font-bold">{{ t('admin.overview.byCountry') }}</h2>
          <dl class="m-0 grid grid-cols-[1fr_auto] gap-y-1.5 text-[15px]">
            <template v-for="(n, c) in list.data.value.by_country" :key="c">
              <dt>{{ c === '—' ? '—' : country(String(c)) }}</dt><dd class="m-0 text-right font-semibold tabular-nums">{{ n }}</dd>
            </template>
          </dl>
        </div>
      </section>

      <section class="overflow-x-auto rounded-card border border-line bg-surface">
        <table class="w-full min-w-[560px] border-collapse text-[15px]">
          <thead>
            <tr class="text-left text-[13px] text-muted">
              <th class="px-4 py-2 font-semibold">{{ t('auth.email') }}</th>
              <th class="px-2 py-2 font-semibold">{{ t('admin.waitlist.role') }}</th>
              <th class="px-2 py-2 font-semibold">{{ t('auth.country') }}</th>
              <th class="px-2 py-2 font-semibold">{{ t('common.language') }}</th>
              <th class="px-4 py-2 font-semibold">{{ t('admin.waitlist.when') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in list.data.value.items" :key="String(r.email)" class="border-t border-ground">
              <td class="px-4 py-2.5 font-semibold">{{ r.email }}</td>
              <td class="px-2 py-2.5">{{ t(`admin.waitlist.roles.${r.role}`) }}</td>
              <td class="px-2 py-2.5">{{ r.country ?? '—' }}</td>
              <td class="px-2 py-2.5">{{ r.locale }}</td>
              <td class="px-4 py-2.5 text-muted">{{ dateTime(String(r.created_at)) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <p class="m-0 text-[14px] text-muted">{{ t('admin.waitlist.privacy') }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIEmpty } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { dateTime } from '@/lib/format'

const { t, locale } = useI18n()
const list = useQuery({
  queryKey: ['admin-waitlist'],
  queryFn: () => call(client.GET('/api/v1/admin/waitlist', { params: { query: { limit: 500 } } })),
})
const names = new Intl.DisplayNames([locale.value], { type: 'region' })
const country = (c: string) => names.of(c) ?? c
</script>
