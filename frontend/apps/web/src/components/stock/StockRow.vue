<template>
  <li
    class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-[14px] border border-line bg-surface py-2.5 pr-2.5 pl-3.5 lg:grid-cols-[minmax(0,2.2fr)_minmax(0,1.2fr)_minmax(0,1fr)_6rem_auto] lg:rounded-none lg:border-0 lg:border-b lg:py-2 lg:pl-4"
  >
    <div class="flex min-w-0 flex-col gap-0.5">
      <RouterLink
        :to="{ name: 'item', params: { id: item.id } }"
        class="truncate text-[16px] leading-snug font-semibold text-ink no-underline hover:underline"
      >{{ item.name }}</RouterLink>
      <span v-if="item.my_name" class="truncate text-[14px] text-ink">{{ item.my_name }}</span>
      <span class="truncate text-[14px] text-muted lg:hidden">{{ [code, place].filter(Boolean).join(' · ') }}</span>
      <span
        v-if="item.catalog_status === 'pending'"
        class="self-start rounded-md bg-primary-soft px-2 py-px text-xs font-semibold"
      >{{ t('item.review.short') }}</span>
      <span
        v-if="item.needs_reorder"
        class="self-start rounded-md bg-warn-bg px-2 py-px text-xs font-semibold text-warn"
      >{{ t('stock.low', { min: item.min_quantity }) }}</span>
    </div>
    <span class="hidden truncate text-[15px] text-muted lg:block">{{ code }}</span>
    <span class="hidden truncate text-[15px] text-muted lg:block">{{ place }}</span>
    <span class="hidden text-right text-[15px] font-semibold lg:block">{{ money(item.sale_price, item.sale_currency) }}</span>
    <!-- Quantity changes only through Sold / Brought / Broken / Move on the item page -->
    <span
      class="min-w-12 text-right text-[18px] font-bold tabular-nums lg:w-20"
      :class="item.quantity === 0 ? 'text-muted' : item.needs_reorder ? 'text-warn' : 'text-ink'"
    >{{ t('common.pcs', { n: item.quantity }) }}</span>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { money } from '@/lib/format'
import type { Item } from '@/lib/queries'

const props = defineProps<{ item: Item; places: Map<string, string> }>()
const { t } = useI18n()

const code = computed(() => {
  const own = [props.item.brand, props.item.code].filter(Boolean).join(' ')
  if (own) return own
  const c = props.item.catalog_item?.codes[0]
  return c ? `${c.brand} ${c.code}` : t(`kinds.${props.item.kind}`)
})
const place = computed(() => {
  const lv = [...props.item.levels].sort((a, b) => b.quantity - a.quantity)
  if (!lv.length) return ''
  const first = props.places.get(lv[0].location_id) ?? ''
  return lv.length > 1 ? `${first} +${lv.length - 1}` : first
})
</script>
