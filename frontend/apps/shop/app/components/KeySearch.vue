<template>
  <form role="search" class="flex gap-2" :action="path('/keys')" method="get" @submit.prevent="go">
    <label class="flex h-[52px] min-w-0 flex-1 items-center gap-2.5 rounded-control border-2 border-line-strong bg-surface px-3 text-muted focus-within:border-ink">
      <UIIcon name="search" :size="22" />
      <input v-model="q" name="q" type="search" :placeholder="t('home.search')" :aria-label="t('home.search')" class="min-w-0 flex-1 bg-transparent text-[17px] text-ink outline-none" />
    </label>
    <UIButton type="submit" size="lg">{{ t('home.find') }}</UIButton>
  </form>
</template>

<script setup lang="ts">
import { UIButton, UIIcon } from '@kv/ui'

const props = defineProps<{ initial?: string }>()
const { t, path } = useLang()
const q = ref(props.initial ?? '')
watch(() => props.initial, (v) => (q.value = v ?? ''))
const go = () => navigateTo({ path: path('/keys'), query: q.value.trim() ? { q: q.value.trim() } : {} })
</script>
