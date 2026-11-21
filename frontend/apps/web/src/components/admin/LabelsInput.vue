<template>
  <div class="flex flex-col gap-2">
    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <UIField
        v-for="l in REQUIRED"
        :key="l"
        :model-value="model[l] ?? ''"
        :label="`${label} · ${l.toUpperCase()}`"
        :error="showErrors && !model[l]?.trim() ? t('validation.missing') : undefined"
        @update:model-value="set(l, $event)"
      />
    </div>
    <details class="text-[14px]">
      <summary class="cursor-pointer font-semibold text-muted">{{ t('admin.attrs.otherLangs') }}</summary>
      <div class="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <UIField
          v-for="l in OTHER"
          :key="l"
          :model-value="model[l] ?? ''"
          :label="`${label} · ${l.toUpperCase()}`"
          :placeholder="model.en ?? ''"
          @update:model-value="set(l, $event)"
        />
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { UIField } from '@kv/ui'
import { useI18n } from 'vue-i18n'

defineProps<{ label: string; showErrors?: boolean }>()
const model = defineModel<Record<string, string>>({ required: true })
const { t } = useI18n()
const REQUIRED = ['uk', 'en'] as const
const OTHER = ['pl', 'de', 'fr', 'es', 'it'] as const

function set(lang: string, v: string | number | null | undefined) {
  model.value = { ...model.value, [lang]: String(v ?? '') }
}
</script>
