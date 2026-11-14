<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-[15px] font-semibold">{{ label }}</label>
    <div
      class="flex h-12 items-center rounded-control border-2 bg-surface px-3 focus-within:border-ink"
      :class="error ? 'border-danger' : 'border-line-strong'"
    >
      <input
        :id="id"
        v-model="model"
        :type="inputType"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :inputmode="inputmode"
        :required="required"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error || hint ? `${id}-msg` : undefined"
        class="min-w-0 flex-1 bg-transparent text-[16px] outline-none"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="-mr-1 flex size-10 items-center justify-center text-muted"
        :aria-label="showPasswordLabel"
        :aria-pressed="reveal"
        @click="reveal = !reveal"
      >
        <UIIcon name="eye" :size="20" />
      </button>
      <slot name="suffix" />
    </div>
    <p v-if="error" :id="`${id}-msg`" class="text-sm font-medium text-danger">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-msg`" class="text-sm text-muted">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import UIIcon from './UIIcon.vue'

const props = withDefaults(
  defineProps<{
    label: string
    type?: string
    placeholder?: string
    error?: string | null
    hint?: string
    autocomplete?: string
    inputmode?: 'text' | 'decimal' | 'numeric' | 'email' | 'search' | 'tel'
    required?: boolean
    showPasswordLabel?: string
  }>(),
  { type: 'text', showPasswordLabel: 'Show password' },
)
const model = defineModel<string | number | null>()
const id = useId()
const reveal = ref(false)
const inputType = computed(() => (props.type === 'password' && reveal.value ? 'text' : props.type))
</script>
