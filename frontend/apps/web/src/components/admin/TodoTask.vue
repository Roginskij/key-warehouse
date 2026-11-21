<template>
  <section class="flex flex-col rounded-card border bg-surface p-4" :class="quiet ? 'border-line' : 'border-line-strong'">
    <div class="flex items-start gap-3">
      <span class="flex size-11 shrink-0 items-center justify-center rounded-full text-[17px] font-bold" :class="quiet ? 'bg-ground' : 'bg-primary-soft'">{{ count }}</span>
      <div class="flex min-w-0 flex-col">
        <h2 class="m-0 text-[17px] font-bold">{{ title }}</h2>
        <p class="m-0 text-[14px] text-muted">{{ hint }}</p>
      </div>
    </div>
    <div class="mt-2 flex flex-col divide-y divide-ground"><slot /></div>
    <button v-if="more" type="button" class="mt-2 self-start text-[15px] font-semibold underline" @click="emit('more')">{{ more }}</button>
  </section>
</template>

<script setup lang="ts">
defineProps<{ count: number; title: string; hint: string; more?: string; quiet?: boolean }>()
const emit = defineEmits<{ more: [] }>()
</script>
