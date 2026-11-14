<template>
  <label class="flex items-center gap-1.5 text-sm font-semibold">
    <span class="sr-only">{{ t('common.language') }}</span>
    <select
      :value="locale"
      class="h-10 rounded-[10px] border border-line-strong bg-surface px-2 text-[15px]"
      @change="setLocale(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="l in LOCALES" :key="l.code" :value="l.code">{{ l.name }}</option>
    </select>
  </label>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { LOCALES, setLocale } from '@/i18n'

const { locale, t } = useI18n()
</script>
