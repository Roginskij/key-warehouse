import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Toast {
  id: number
  text: string
  action?: { label: string; run: () => void | Promise<void> }
  tone?: 'info' | 'error'
}

/** One message at a time at the bottom: "−1 · HU66 · Undo" instead of "are you sure?". */
export const useToast = defineStore('toast', () => {
  const current = ref<Toast | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  let seq = 0

  function show(text: string, opts: { action?: Toast['action']; tone?: Toast['tone']; ms?: number } = {}) {
    clearTimeout(timer)
    current.value = { id: ++seq, text, action: opts.action, tone: opts.tone ?? 'info' }
    timer = setTimeout(() => (current.value = null), opts.ms ?? 5000)
  }
  function error(text: string) {
    show(text, { tone: 'error', ms: 6000 })
  }
  function close() {
    clearTimeout(timer)
    current.value = null
  }
  return { current, show, error, close }
})
