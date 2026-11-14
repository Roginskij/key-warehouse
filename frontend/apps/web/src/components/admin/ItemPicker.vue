<template>
  <div class="flex flex-col gap-1.5">
    <label class="flex flex-col gap-1.5">
      <span class="text-[15px] font-semibold">{{ label }}</span>
      <span class="flex h-12 items-center gap-2 rounded-control border-2 border-line-strong bg-surface px-3 focus-within:border-ink">
        <UIIcon name="search" :size="20" class="text-muted" />
        <input v-model="text" type="search" :placeholder="placeholder" class="min-w-0 flex-1 bg-transparent text-[16px] outline-none" />
      </span>
    </label>
    <ul v-if="results.length" class="m-0 flex list-none flex-col divide-y divide-ground rounded-control border border-line bg-surface p-0">
      <li v-for="i in results" :key="i.id">
        <button type="button" class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-ground" @click="choose(i)">
          <span class="font-semibold">{{ i.name }}</span>
          <span class="text-[14px] text-muted">{{ i.codes.map((c) => `${c.brand} ${c.code}`).join(' · ') }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIIcon } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { call, client } from '@/lib/api'

/** Search the catalog and pick one item (for merge / substitutes). */
const props = defineProps<{ label: string; placeholder?: string; excludeId?: string }>()
const emit = defineEmits<{ pick: [Schemas['ItemAdminOut']] }>()
const text = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(text, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (q.value = v.trim()), 250)
})
const { data } = useQuery({
  queryKey: computed(() => ['admin-picker', q.value]),
  queryFn: () => call(client.GET('/api/v1/admin/catalog/items', { params: { query: { q: q.value, status: ['active'], limit: 8 } } })),
  enabled: computed(() => q.value.length >= 2),
})
const results = computed(() => (data.value?.items ?? []).filter((i) => i.id !== props.excludeId))
function choose(i: Schemas['ItemAdminOut']) {
  emit('pick', i)
  text.value = ''
  q.value = ''
}
</script>
