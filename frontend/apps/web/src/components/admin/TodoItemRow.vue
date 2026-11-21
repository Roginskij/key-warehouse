<template>
  <RouterLink :to="{ name: 'admin-item', params: { id: item.id } }" class="flex items-center gap-3 py-2.5 text-ink no-underline">
    <span class="flex min-w-0 flex-1 flex-col">
      <b class="truncate">{{ item.name }}</b>
      <span class="truncate text-[14px] text-muted">{{ item.codes.join(' · ') }}</span>
    </span>
    <span v-if="item.workshops" class="shrink-0 text-[13px] text-muted">{{ t('admin.todo.inWorkshops', { n: item.workshops }) }}</span>
    <span class="hidden shrink-0 text-[14px] font-semibold sm:inline">{{ action }}</span>
    <UIIcon name="chevron" :size="20" class="shrink-0 text-faint" />
  </RouterLink>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIIcon } from '@kv/ui'
import { useI18n } from 'vue-i18n'

defineProps<{ item: Schemas['TodoItem']; action: string }>()
const { t } = useI18n()
</script>
