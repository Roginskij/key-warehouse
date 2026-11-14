<template>
  <header
    class="flex flex-col gap-3 bg-graphite px-4 pt-3 pb-4 text-on-graphite md:bg-transparent md:px-0 md:pt-7 md:pb-5 md:text-ink"
  >
    <RouterLink
      v-if="back"
      :to="back"
      class="-ml-1.5 flex h-10 items-center gap-0.5 self-start pr-2 text-[16px] font-semibold text-primary no-underline md:text-ink"
    >
      <UIIcon name="back" :size="24" :stroke="2.2" />{{ backLabel }}
    </RouterLink>
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div class="flex min-w-0 flex-col gap-0.5">
        <span v-if="subtitle" class="text-sm text-on-graphite-muted md:text-muted">{{ subtitle }}</span>
        <h1 class="m-0 text-[26px] leading-tight font-bold tracking-tight md:text-[30px]">{{ title }}</h1>
      </div>
      <div class="flex flex-wrap items-center gap-2"><slot name="actions" /></div>
    </div>
    <slot />
  </header>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
import type { RouteLocationRaw } from 'vue-router'

defineProps<{ title: string; subtitle?: string; back?: RouteLocationRaw; backLabel?: string }>()
</script>
