<template>
  <div class="flex flex-col items-center gap-2 rounded-card border border-line bg-surface px-6 py-8 text-center">
    <span v-if="icon" class="flex size-13 items-center justify-center rounded-full bg-primary-soft text-ink">
      <UIIcon :name="icon" :size="26" />
    </span>
    <p class="m-0 text-lg font-bold">{{ title }}</p>
    <p v-if="text" class="m-0 max-w-sm text-[15px] text-muted">{{ text }}</p>
    <div class="mt-2 flex flex-wrap justify-center gap-2"><slot /></div>
  </div>
</template>

<script setup lang="ts">
import UIIcon from './UIIcon.vue'
defineProps<{ icon?: string; title: string; text?: string }>()
</script>
