<template>
  <div class="flex items-center gap-1">
    <button
      type="button"
      :class="box[size]"
      class="flex items-center justify-center border-2 border-line-strong bg-surface text-ink disabled:opacity-35"
      :disabled="value <= 0 || busy"
      :aria-label="minusLabel"
      @click="$emit('minus')"
    >
      <UIIcon name="minus" :size="icon[size]" :stroke="2.6" />
    </button>
    <span :class="num[size]" class="text-center font-bold tabular-nums" aria-live="polite">{{ value }}</span>
    <button
      type="button"
      :class="box[size]"
      class="flex items-center justify-center bg-primary text-on-primary hover:bg-primary-hover disabled:opacity-35"
      :disabled="busy"
      :aria-label="plusLabel"
      @click="$emit('plus')"
    >
      <UIIcon name="plus" :size="icon[size]" :stroke="2.6" />
    </button>
  </div>
</template>

<script setup lang="ts">
import UIIcon from './UIIcon.vue'

withDefaults(
  defineProps<{
    value: number
    size?: 'sm' | 'md' | 'lg'
    minusLabel?: string
    plusLabel?: string
    busy?: boolean
  }>(),
  { size: 'md', minusLabel: '−1', plusLabel: '+1' },
)
defineEmits<{ minus: []; plus: [] }>()

const box = { sm: 'size-9 rounded-[10px]', md: 'size-11 rounded-control', lg: 'size-[52px] rounded-[14px]' }
const num = { sm: 'min-w-8 text-[17px]', md: 'min-w-9 text-xl', lg: 'min-w-16 text-[38px]' }
const icon = { sm: 16, md: 20, lg: 26 }
</script>
