<template>
  <NuxtLayout>
    <div class="flex flex-col items-start gap-3 py-10">
      <h1 class="m-0 text-[28px] font-bold">{{ error?.statusCode === 404 ? t('notFound.title') : 'Error' }}</h1>
      <p class="m-0 text-muted">{{ t('notFound.text') }}</p>
      <NuxtLink :to="path('/keys')" :class="buttonClass('primary', 'lg')">{{ t('keys.all') }}</NuxtLink>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
import { buttonClass } from '@kv/ui'
import type { NuxtError } from '#app'

defineProps<{ error: NuxtError }>()
const { t, path } = useLang()
useSeoMeta({ robots: 'noindex' })
</script>
