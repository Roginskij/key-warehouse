<template>
  <PageHeader :title="w?.name ?? '…'" :back="{ name: 'admin-workshops' }" :back-label="t('admin.workshops.title')" />
  <div v-if="detail.isError.value && !w" class="p-3 md:p-0"><LoadError :error="detail.error.value" @retry="detail.refetch()" /></div>
  <div v-else-if="detail.isPending.value" class="m-3 h-40 animate-pulse rounded-card bg-surface md:mx-0" />

  <div v-else-if="w" class="grid grid-cols-1 gap-4 p-3 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
    <div class="flex flex-col gap-4">
      <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4 text-[15px]">
        <dl class="m-0 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
          <dt class="text-muted">{{ t('auth.country') }}</dt><dd class="m-0">{{ country(w.country) }}<template v-if="w.city">, {{ w.city }}</template></dd>
          <dt class="text-muted">{{ t('admin.workshops.created') }}</dt><dd class="m-0">{{ dateTime(w.created_at) }}</dd>
          <dt class="text-muted">{{ t('admin.workshops.itemsLabel') }}</dt><dd class="m-0">{{ w.items }}</dd>
          <dt class="text-muted">{{ t('admin.workshops.activity') }}</dt><dd class="m-0">{{ w.last_activity ? dateTime(w.last_activity) : '—' }}</dd>
          <dt class="text-muted">{{ t('admin.workshops.site') }}</dt><dd class="m-0">{{ w.public_listed ? t('admin.workshops.onSite') : '—' }}</dd>
          <dt class="text-muted">{{ t('publicProfile.taxId') }}</dt><dd class="m-0">{{ w.tax_id ?? '—' }} <span class="text-muted">· {{ t(`publicProfile.statuses.${w.verification_status}`) }}</span></dd>
        </dl>
      </section>
      <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ t('team.members') }}</h2>
        <div v-for="m in w.members_list" :key="m.email" class="flex flex-col border-b border-ground py-2 last:border-0">
          <b>{{ m.full_name }}</b>
          <span class="truncate text-[14px] text-muted">{{ m.email }} · {{ t(`roles.${m.role}`) }}</span>
        </div>
      </section>
    </div>

    <!-- Stock: superadmin only; customers are never shown here -->
    <section v-if="session.isSuperadmin" class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('admin.workshops.stock') }}</h2>
      <input v-model="search" type="search" :placeholder="t('stock.search')" :aria-label="t('stock.search')" class="h-11 rounded-control border-2 border-line-strong px-3 outline-none focus:border-ink" />
      <LoadError v-if="stock.isError.value" :error="stock.error.value" @retry="stock.refetch()" />
      <p v-else-if="stock.data.value && !stock.data.value.items.length" class="m-0 text-muted">{{ t('admin.workshops.noItems') }}</p>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[520px] border-collapse text-[15px]">
          <thead>
            <tr class="text-left text-[13px] text-muted">
              <th class="py-2 pr-2 font-semibold">{{ t('item.form.name') }}</th>
              <th class="px-2 py-2 font-semibold">{{ t('item.form.code') }}</th>
              <th class="px-2 py-2 text-right font-semibold">{{ t('admin.workshops.qty') }}</th>
              <th class="px-2 py-2 text-right font-semibold">{{ t('item.salePrice') }}</th>
              <th class="py-2 pl-2 font-semibold">{{ t('admin.nav.catalog') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in stock.data.value?.items" :key="i.id" class="border-t border-ground">
              <td class="py-2 pr-2 font-semibold">{{ i.name }}</td>
              <td class="px-2 py-2 text-muted">{{ [i.brand, i.code].filter(Boolean).join(' ') || '—' }}</td>
              <td class="px-2 py-2 text-right tabular-nums" :class="i.quantity < i.min_quantity ? 'font-bold text-warn' : ''">{{ i.quantity }}</td>
              <td class="px-2 py-2 text-right tabular-nums">{{ i.sale_price ? `${i.sale_price} ${i.sale_currency ?? ''}` : '—' }}</td>
              <td class="py-2 pl-2">{{ i.linked_to_catalog ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { dateTime } from '@/lib/format'
import { useSession } from '@/stores/session'

const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()
const session = useSession()
const path = computed(() => ({ workshop_id: props.id }))

const detail = useQuery({
  queryKey: computed(() => ['admin-workshop', props.id]),
  queryFn: () => call(client.GET('/api/v1/admin/workshops/{workshop_id}', { params: { path: path.value } })),
})
const w = computed(() => detail.data.value)

const search = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (q.value = v.trim()), 300)
})
const stock = useQuery({
  queryKey: computed(() => ['admin-workshop-stock', props.id, q.value]),
  queryFn: () => call(client.GET('/api/v1/admin/workshops/{workshop_id}/stock', { params: { path: path.value, query: { q: q.value || undefined } } })),
  enabled: computed(() => session.isSuperadmin),
  placeholderData: keepPreviousData,
})
const country = (c: string) => new Intl.DisplayNames([locale.value], { type: 'region' }).of(c) ?? c
</script>
