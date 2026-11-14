<template>
  <div role="alert" class="flex flex-col items-center gap-3 rounded-card border border-line bg-surface px-6 py-8 text-center">
    <span class="flex size-12 items-center justify-center rounded-full bg-danger-bg text-danger"><UIIcon name="close" :size="24" :stroke="2.6" /></span>
    <p class="m-0 text-lg font-bold">{{ t('common.loadErrorTitle') }}</p>
    <p class="m-0 max-w-sm text-[15px] text-muted">{{ errorText(error) }}</p>
    <UIButton variant="outline" @click="$emit('retry')">{{ t('common.retry') }}</UIButton>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIIcon } from '@kv/ui'
import { useI18n } from 'vue-i18n'
import { errorText } from '@/lib/errors'

/** A failed load: what happened and a way to try again — never a blank page. */
defineProps<{ error: unknown }>()
defineEmits<{ retry: [] }>()
const { t } = useI18n()
</script>
