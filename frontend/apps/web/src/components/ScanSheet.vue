<template>
  <Sheet :open="open" :title="t('scan.title')" :close-label="t('common.close')" @close="emit('close')">
    <div class="relative overflow-hidden rounded-control bg-ink" style="aspect-ratio: 1 / 1">
      <video ref="video" class="size-full object-cover" muted playsinline />
      <p v-if="starting" class="absolute inset-0 m-0 flex items-center justify-center text-white">{{ t('scan.starting') }}</p>
    </div>
    <p v-if="error" role="alert" class="m-0 rounded-control bg-danger-bg p-3 text-[15px] text-danger">{{ error }}</p>
    <p v-else class="m-0 text-[15px] text-muted">{{ t('scan.hint') }}</p>
  </Sheet>
</template>

<script setup lang="ts">
import QrScanner from 'qr-scanner'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Sheet from '@/components/Sheet.vue'
import { stickerPath } from '@/lib/qr'

/** Scan a box sticker with the camera and open that place's stock. */
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const router = useRouter()
const video = ref<HTMLVideoElement>()
const error = ref('')
const starting = ref(false)
let scanner: QrScanner | null = null
let wrongShown = false

async function start() {
  error.value = ''
  wrongShown = false
  if (!video.value) return
  starting.value = true
  scanner = new QrScanner(
    video.value,
    (result) => {
      const path = stickerPath(result.data)
      if (path) {
        stop()
        emit('close')
        router.push(path)
      } else if (!wrongShown) {
        wrongShown = true
        error.value = t('scan.notOurs')
      }
    },
    { returnDetailedScanResult: true, highlightScanRegion: true, preferredCamera: 'environment' },
  )
  try {
    await scanner.start()
  } catch {
    error.value = window.isSecureContext ? t('scan.noCamera') : t('scan.needsHttps')
  } finally {
    starting.value = false
  }
}
function stop() {
  scanner?.stop()
  scanner?.destroy()
  scanner = null
}

watch(
  () => props.open,
  (v) => (v ? setTimeout(start, 50) : stop()),
  { immediate: true },
)
onBeforeUnmount(stop)
</script>
