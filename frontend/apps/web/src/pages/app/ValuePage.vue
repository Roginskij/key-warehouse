<template>
  <PageHeader :title="t('value.title')" :subtitle="t('value.subtitle')" :back="{ name: 'stock' }" :back-label="t('nav.stock')" />
  <div class="flex flex-col gap-3 p-3 md:max-w-3xl md:p-0 md:pb-12">
    <UIEmpty v-if="!session.seesPurchase" icon="eye" :title="t('value.hiddenTitle')" :text="t('value.hiddenText')" />
    <LoadError v-else-if="isError && !v" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-36 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="v && !v.by_currency.length && !v.items_without_purchase_price" icon="coins" :title="t('value.emptyTitle')" :text="t('value.emptyText')">
      <RouterLink :to="{ name: 'stock' }" :class="buttonClass('primary', 'md')">{{ t('nav.stock') }}</RouterLink>
    </UIEmpty>
    <template v-else-if="v">
      <section class="flex flex-col gap-1 rounded-card border border-line bg-surface p-5">
        <span class="text-[15px] text-muted">{{ t('value.total') }}</span>
        <span class="text-[40px] leading-tight font-bold tabular-nums">{{ money(v.total_in_base, v.base_currency) }}</span>
        <span class="text-[14px] text-muted">{{ t('value.atPurchase') }}</span>
      </section>

      <section v-if="v.by_currency.length" class="rounded-card border border-line bg-surface px-4 py-1">
        <h2 class="m-0 pt-3 pb-1 text-[16px] font-bold">{{ t('value.byCurrency') }}</h2>
        <dl class="m-0 divide-y divide-ground">
          <div v-for="c in v.by_currency" :key="c.currency" class="flex min-h-12 items-center justify-between gap-3">
            <dt class="text-muted">{{ c.currency }} · {{ t('value.items', { n: num(c.items) }) }}</dt>
            <dd class="m-0 font-semibold tabular-nums">{{ money(c.amount, c.currency) }}</dd>
          </div>
        </dl>
      </section>

      <div v-if="v.currencies_without_rate.length" class="flex flex-col gap-2 rounded-card bg-warn-bg p-4 text-warn">
        <p class="m-0 font-semibold">{{ t('value.noRate', { list: v.currencies_without_rate.join(', '), base: v.base_currency }) }}</p>
        <RouterLink v-if="session.isOwner" :to="{ name: 'more' }" class="self-start font-bold text-warn">{{ t('value.setRate') }}</RouterLink>
        <p v-else class="m-0 text-[15px]">{{ t('value.askOwner') }}</p>
      </div>
      <p v-else-if="foreign.length" class="m-0 px-1 text-[14px] text-muted">{{ t('value.converted', { base: v.base_currency }) }}</p>

      <div v-if="v.items_without_purchase_price" class="flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface p-4">
        <UIIcon name="edit" :size="20" class="text-muted" />
        <span class="flex-1">{{ t('value.noPrice', { n: num(v.items_without_purchase_price) }) }}</span>
        <RouterLink :to="{ name: 'stock' }" :class="buttonClass('outline', 'sm')">{{ t('nav.stock') }}</RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIEmpty, UIIcon } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { money, num } from '@/lib/format'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const session = useSession()
const { data: v, isPending, isError, error, refetch } = useQuery({
  queryKey: computed(() => ['value', session.wid]),
  queryFn: () =>
    call(client.GET('/api/v1/workshops/{workshop_id}/inventory/value', { params: { path: { workshop_id: session.wid } } })),
  enabled: computed(() => !!session.wid && session.seesPurchase),
})
const foreign = computed(() => (v.value?.by_currency ?? []).filter((c) => c.currency !== v.value?.base_currency))
</script>
