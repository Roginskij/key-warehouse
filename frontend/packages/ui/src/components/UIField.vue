<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-[15px] font-semibold">{{ label }}</label>
    <div
      class="flex h-12 items-center rounded-control border-2 bg-surface px-3 focus-within:border-ink"
      :class="error ? 'border-danger' : 'border-line-strong'"
    >
      <input
        :id="id"
        :value="model ?? ''"
        :type="inputType"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :inputmode="inputmode"
        :required="required"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error || hint ? `${id}-msg` : undefined"
        class="min-w-0 flex-1 bg-transparent text-[16px] outline-none"
        @input="onInput"
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
    /** For inputmode="decimal": at most this many digits after the separator (prices: 2). */
    decimals?: number
    required?: boolean
    showPasswordLabel?: string
  }>(),
  { type: 'text', showPasswordLabel: 'Show password' },
)
const model = defineModel<string | number | null>()
const id = useId()
const reveal = ref(false)
const inputType = computed(() => (props.type === 'password' && reveal.value ? 'text' : props.type))

/** Number fields accept only what makes a number: "numeric" — digits; "decimal" — digits
 *  and one "," or "." (keyboards in Ukraine/EU type a comma). Letters never get in. */
function clean(raw: string): string {
  if (props.inputmode === 'numeric') return raw.replace(/\D/g, '')
  if (props.inputmode !== 'decimal') return raw
  let v = raw.replace(/[^\d.,]/g, '')
  const sep = v.search(/[.,]/)
  if (sep >= 0) {
    const fraction = v.slice(sep + 1).replace(/[.,]/g, '')
    v = v.slice(0, sep + 1) + (props.decimals !== undefined ? fraction.slice(0, props.decimals) : fraction)
  }
  return v
}
function onInput(e: Event) {
  const el = e.target as HTMLInputElement
  const v = clean(el.value)
  if (el.value !== v) el.value = v // drop the rejected character right away
  model.value = v
}
</script>
