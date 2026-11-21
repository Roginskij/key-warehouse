<template>
  <div class="flex flex-col gap-3">
    <label class="flex h-[52px] items-center gap-2.5 rounded-control border-2 border-line-strong bg-surface px-3 text-muted focus-within:border-ink">
      <UIIcon name="search" :size="22" />
      <input
        ref="input"
        v-model="search"
        type="search"
        :placeholder="t('item.pick.placeholder')"
        :aria-label="t('item.pick.placeholder')"
        class="min-w-0 flex-1 bg-transparent text-[17px] text-ink outline-none"
      />
    </label>
    <p v-if="!q" class="m-0 text-[14px] text-muted">{{ t('item.pick.hint') }}</p>
    <p v-else-if="results.isFetching.value && !items.length" class="m-0 text-[14px] text-muted">…</p>
    <p v-else-if="!items.length" class="m-0 text-[15px]">{{ t('item.pick.nothing', { q }) }}</p>
    <ul v-if="items.length" class="m-0 flex flex-col divide-y divide-ground rounded-card border border-line bg-surface p-0">
      <li v-for="c in items" :key="c.id" class="list-none">
        <button type="button" class="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-ground" @click="emit('pick', c)">
          <span class="flex min-w-0 flex-1 flex-col">
            <b class="truncate">{{ c.name }}</b>
            <span class="text-[13px] text-muted">{{ t(`kinds.${c.kind}`) }}</span>
            <span class="truncate text-[14px] text-muted">{{ c.codes.map((x) => `${x.brand} ${x.code}`).join(' · ') }}</span>
          </span>
          <UIIcon name="chevron" :size="20" class="shrink-0 text-faint" />
        </button>
      </li>
    </ul>
    <button type="button" class="self-start text-[15px] font-semibold underline" @click="emit('manual', search.trim())">
      {{ t('item.pick.notThere') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIIcon } from '@kv/ui'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { call, client } from '@/lib/api'

const emit = defineEmits<{ pick: [Schemas['ItemOut']]; manual: [string] }>()
const { t } = useI18n()

const input = ref<HTMLInputElement | null>(null)
onMounted(() => input.value?.focus())
const search = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (q.value = v.trim()), 250)
})
const results = useQuery({
  queryKey: computed(() => ['catalog-pick', q.value]),
  queryFn: () => call(client.GET('/api/v1/catalog/items', { params: { query: { q: q.value, limit: 15 } } })),
  enabled: computed(() => q.value.length >= 2),
  placeholderData: keepPreviousData,
})
const items = computed(() => (q.value ? (results.data.value?.items ?? []) : []))
</script>
