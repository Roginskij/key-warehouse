<template>
  <dialog
    ref="el"
    class="m-0 mt-auto w-full max-w-none rounded-t-[20px] border-0 bg-surface p-0 text-ink backdrop:bg-black/40 sm:m-auto sm:max-w-md sm:rounded-[20px]"
    @close="emit('close')"
    @click.self="emit('close')"
  >
    <div class="flex flex-col gap-4 p-5 pb-7">
      <div class="flex items-center justify-between gap-3">
        <h2 class="m-0 text-xl font-bold">{{ title }}</h2>
        <button type="button" class="flex size-10 items-center justify-center rounded-full hover:bg-black/5" :aria-label="closeLabel ?? 'Close'" @click="emit('close')">
          <UIIcon name="close" :size="22" />
        </button>
      </div>
      <slot />
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
import { onMounted, ref, watch } from 'vue'

/** Bottom sheet on phones, centered dialog on desktop. Uses native <dialog> (focus trap, Esc). */
const props = defineProps<{ open: boolean; title: string; closeLabel?: string }>()
const emit = defineEmits<{ close: [] }>()
const el = ref<HTMLDialogElement>()

watch(
  () => props.open,
  (v) => {
    if (!el.value) return
    if (v && !el.value.open) el.value.showModal()
    if (!v && el.value.open) el.value.close()
  },
  { flush: 'post' },
)
onMounted(() => {
  if (props.open && el.value && !el.value.open) el.value.showModal()
})
</script>
