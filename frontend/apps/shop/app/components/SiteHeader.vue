<template>
  <header class="bg-graphite text-on-graphite">
    <div class="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
      <NuxtLink :to="path()" class="flex items-center gap-2 text-[19px] font-bold text-on-graphite no-underline">
        <span class="flex size-8 items-center justify-center rounded-lg bg-primary text-on-primary"><UIIcon name="key" :size="18" /></span>
        KeyVerhaus
      </NuxtLink>
      <nav class="flex flex-1 items-center gap-1 text-[15px] font-semibold" :aria-label="t('site.keys')">
        <NuxtLink :to="path('/keys')" class="rounded-lg px-3 py-2 text-on-graphite-muted no-underline hover:bg-graphite-2 hover:text-on-graphite">{{ t('site.keys') }}</NuxtLink>
        <NuxtLink :to="path('/workshops')" class="rounded-lg px-3 py-2 text-on-graphite-muted no-underline hover:bg-graphite-2 hover:text-on-graphite">{{ t('site.workshops') }}</NuxtLink>
      </nav>
      <a :href="appUrl" class="hidden text-[14px] font-semibold text-primary no-underline sm:inline">{{ t('site.app') }}</a>
    </div>
  </header>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'

const { t, path } = useLang()
const { appUrl } = useRuntimeConfig().public
</script>
