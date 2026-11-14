<template>
  <Transition
    enter-from-class="translate-y-4 opacity-0"
    leave-to-class="translate-y-4 opacity-0"
    enter-active-class="transition duration-150"
    leave-active-class="transition duration-150"
  >
    <div
      v-if="toast.current"
      :key="toast.current.id"
      role="status"
      class="print:hidden fixed inset-x-3 bottom-[76px] z-50 mx-auto flex min-h-12 max-w-md items-center justify-between gap-3 rounded-control py-1 pr-1.5 pl-4 text-white shadow-lg md:bottom-6"
      :class="toast.current.tone === 'error' ? 'bg-danger' : 'bg-ink'"
    >
      <span class="truncate text-[15px] font-medium">{{ toast.current.text }}</span>
      <button
        v-if="toast.current.action"
        type="button"
        class="h-10 shrink-0 rounded-[10px] px-3 text-[15px] font-bold text-primary hover:bg-white/10"
        @click="act"
      >
        {{ toast.current.action.label }}
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useToast } from '@/stores/toast'

const toast = useToast()

async function act() {
  const a = toast.current?.action
  toast.close()
  await a?.run()
}
</script>
