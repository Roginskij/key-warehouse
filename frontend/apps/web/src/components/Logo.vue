<template>
  <span class="flex items-center gap-2.5">
    <span class="flex size-9 items-center justify-center rounded-[10px] bg-primary text-on-primary">
      <UIIcon name="key" :size="22" :stroke="2.2" />
    </span>
    <span class="text-lg font-bold tracking-tight" :class="dark ? 'text-on-graphite' : 'text-ink'">KeyVerhaus</span>
  </span>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
defineProps<{ dark?: boolean }>()
</script>
