<template>
  <NuxtLink :to="path(`/keys/${item.slug}`)" class="flex items-center gap-3 rounded-card border border-line bg-surface p-3 text-ink no-underline hover:border-line-strong">
    <img v-if="item.image" :src="item.image" :alt="item.name" width="64" height="64" loading="lazy" class="size-16 shrink-0 rounded-control bg-ground object-contain" />
    <span v-else class="flex size-16 shrink-0 items-center justify-center rounded-control bg-primary-soft"><UIIcon name="key" :size="26" /></span>
    <span class="flex min-w-0 flex-col gap-0.5">
      <span class="font-bold">{{ item.name }}</span>
      <span class="text-[13px] text-muted">{{ t(`kinds.${item.kind}`) }}</span>
      <span class="truncate text-[14px] text-muted">{{ item.codes.map((c) => `${c.brand} ${c.code}`).join(' · ') }}</span>
    </span>
  </NuxtLink>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'

defineProps<{ item: PublicKeyBrief }>()
const { t, path } = useLang()
</script>
