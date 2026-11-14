<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-[15px] font-semibold">{{ label }}</label>
    <select
      :id="id"
      v-model="model"
      class="h-12 rounded-control border-2 bg-surface px-2.5 text-[16px] outline-none focus:border-ink"
      :class="error ? 'border-danger' : 'border-line-strong'"
    >
      <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <p v-if="error" class="text-sm font-medium text-danger">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { useId } from 'vue'

defineProps<{
  label: string
  options: { value: string; label: string }[]
  error?: string | null
}>()
const model = defineModel<string | null>()
const id = useId()
</script>
