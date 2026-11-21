<template>
  <PageHeader :title="t('stock.title')" :subtitle="session.workshop?.workshop_name">
    <template #actions>
      <span class="text-sm text-on-graphite-muted md:mr-2 md:text-muted">
        {{ t('stock.summary', { items: num(data?.total ?? 0), pieces: num(pieces) }) }}
      </span>
      <div class="hidden gap-2 md:flex">
        <UIButton variant="outline" @click="exportExcel">
          <UIIcon name="download" :size="18" />{{ t('stock.export') }}
        </UIButton>
        <RouterLink :to="{ name: 'item-new' }" :class="buttonClass('primary', 'md')">
          <UIIcon name="plus" :size="18" :stroke="2.6" />{{ t('stock.add') }}
        </RouterLink>
      </div>
    </template>
    <div class="flex gap-2 md:max-w-xl">
    <label
      class="flex h-12 min-w-0 flex-1 items-center gap-2.5 rounded-control border-2 border-graphite-2 bg-graphite-2 px-3 text-on-graphite-muted focus-within:border-primary md:max-w-xl md:border-line-strong md:bg-surface md:text-muted md:focus-within:border-ink"
    >
      <UIIcon name="search" :size="22" />
      <input
        v-model="search"
        type="search"
        :placeholder="t('stock.searchPlaceholder')"
        :aria-label="t('stock.search')"
        class="min-w-0 flex-1 bg-transparent text-[16px] text-on-graphite outline-none placeholder:text-on-graphite-muted md:text-ink md:placeholder:text-faint"
      />
    </label>
    <button
      type="button"
      class="flex size-12 shrink-0 items-center justify-center rounded-control border-2 border-graphite-2 bg-graphite-2 text-primary md:border-line-strong md:bg-surface md:text-ink"
      :aria-label="t('scan.button')"
      @click="scanOpen = true"
    >
      <UIIcon name="scan" :size="24" />
    </button>
    </div>
    <div class="-mx-4 flex gap-2 overflow-x-auto px-4 pb-0.5 md:mx-0 md:flex-wrap md:overflow-visible md:px-0" role="group" :aria-label="t('stock.filter')">
      <button
        v-for="f in FILTERS"
        :key="f"
        type="button"
        class="h-9 shrink-0 rounded-full px-3.5 text-[14px] font-semibold"
        :class="
          filter === f
            ? 'bg-primary text-on-primary'
            : 'border border-graphite-2 bg-graphite-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink'
        "
        :aria-pressed="filter === f"
        @click="filter = f"
      >{{ t(`stock.filters.${f}`) }}</button>
    </div>
  </PageHeader>

  <div class="flex flex-1 flex-col gap-3 p-2.5 pb-24 md:p-0 md:pb-10">
    <div v-if="locationId" class="flex items-center gap-2 px-1.5 text-[15px]">
      <span>{{ t('stock.inLocation', { place: places.get(locationId) ?? '…' }) }}</span>
      <button type="button" class="rounded-full p-1 hover:bg-black/5" :aria-label="t('common.clear')" @click="clearLocation">
        <UIIcon name="close" :size="18" />
      </button>
    </div>

    <LoadError v-if="isError && !data" :error="error" @retry="refetch()" />

    <ul v-else-if="isPending" class="m-0 flex list-none flex-col gap-2 p-0" aria-hidden="true">
      <li v-for="n in 6" :key="n" class="h-[68px] animate-pulse rounded-[14px] bg-surface" />
    </ul>

    <UIEmpty
      v-else-if="!items.length && !hasFilters"
      icon="box"
      :title="route.query.welcome ? t('stock.welcomeTitle') : t('stock.emptyTitle')"
      :text="t('stock.emptyText')"
    >
      <RouterLink :to="{ name: 'import' }" :class="buttonClass('primary', 'lg')">
        <UIIcon name="upload" :size="20" />{{ t('stock.importExcel') }}
      </RouterLink>
      <RouterLink :to="{ name: 'item-new' }" :class="buttonClass('outline', 'lg')">{{ t('stock.addFirst') }}</RouterLink>
    </UIEmpty>

    <UIEmpty v-else-if="!items.length" icon="search" :title="t('stock.nothingFound')" :text="t('stock.nothingFoundText')">
      <RouterLink :to="{ name: 'item-new' }" :class="buttonClass('primary', 'md')">{{ t('stock.add') }}</RouterLink>
    </UIEmpty>

    <section v-else class="lg:overflow-hidden lg:rounded-card lg:border lg:border-line lg:bg-surface">
      <div
        class="hidden grid-cols-[minmax(0,2.2fr)_minmax(0,1.2fr)_minmax(0,1fr)_6rem_auto] gap-3 border-b border-line px-4 py-2.5 text-[13px] font-semibold text-muted lg:grid"
        aria-hidden="true"
      >
        <span>{{ t('stock.cols.name') }}</span><span>{{ t('stock.cols.code') }}</span><span>{{ t('stock.cols.place') }}</span>
        <span class="text-right">{{ t('stock.cols.price') }}</span><span class="w-20 text-right">{{ t('stock.cols.qty') }}</span>
      </div>
      <ul class="m-0 flex list-none flex-col gap-2 p-0 lg:gap-0">
        <StockRow
          v-for="item in items"
          :key="item.id"
          :item="item"
          :places="places"
        />
      </ul>
    </section>
  </div>

  <RouterLink
    :to="{ name: 'item-new' }"
    :class="buttonClass('primary', 'lg')"
    class="fixed right-4 bottom-[80px] z-30 rounded-full pr-6 shadow-lg md:hidden"
  >
    <UIIcon name="plus" :size="22" :stroke="2.6" />{{ t('stock.add') }}
  </RouterLink>
  <ScanSheet v-if="scanOpen" :open="scanOpen" @close="scanOpen = false" />
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIEmpty, UIIcon } from '@kv/ui'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import ScanSheet from '@/components/ScanSheet.vue'
import StockRow from '@/components/stock/StockRow.vue'
import { raw } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { num } from '@/lib/format'
import { useItems, useLocationNames } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const toast = useToast()

const scanOpen = ref(false)
const search = ref(String(route.query.q ?? ''))
const debounced = ref(search.value)
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = v.trim()), 250)
})

const filter = ref<string>(String(route.query.filter ?? 'all'))
const locationId = computed(() => (route.query.location ? String(route.query.location) : null))
const FILTERS = ['all', 'blank', 'car_key', 'remote', 'transponder', 'low'] as const

const filters = computed(() => ({
  q: debounced.value,
  kind: filter.value !== 'all' && filter.value !== 'low' ? filter.value : null,
  low_stock: filter.value === 'low',
  location_id: locationId.value,
}))
const { data, isPending, isError, error, refetch } = useItems(filters)
const places = useLocationNames()
const items = computed(() => data.value?.items ?? [])
const pieces = computed(() => items.value.reduce((s, i) => s + i.quantity, 0))
const hasFilters = computed(() => !!debounced.value || filter.value !== 'all' || !!locationId.value)


async function exportExcel() {
  try {
    const res = await raw(`/api/v1/workshops/${session.wid}/inventory/export`)
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement('a')
    a.href = url
    a.download = `keyverhaus-${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(errorText(e))
  }
}

function clearLocation() {
  const q = { ...route.query }
  delete q.location
  router.replace({ query: q })
}
</script>
