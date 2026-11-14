<template>
  <PageHeader
    :title="t('reorder.title')"
    :subtitle="items.length ? t('reorder.subtitle', { n: items.length }) : undefined"
  />
  <div class="grid flex-1 content-start gap-2.5 p-2.5 md:p-0 md:pb-10 lg:grid-cols-2">
    <LoadError v-if="isError && !data" class="lg:col-span-2" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-24 animate-pulse rounded-card bg-surface lg:col-span-2" />
    <UIEmpty v-else-if="!items.length" class="lg:col-span-2" icon="check" :title="t('reorder.emptyTitle')" :text="t('reorder.emptyText')" />
    <template v-else>
      <article v-for="i in items" :key="i.id" class="flex flex-col gap-3 rounded-[14px] border border-line bg-surface p-4">
        <div class="flex justify-between gap-3">
          <div class="flex min-w-0 flex-col gap-0.5">
            <RouterLink :to="{ name: 'item', params: { id: i.id } }" class="truncate text-[16px] font-semibold text-ink no-underline">{{ i.name }}</RouterLink>
            <span class="text-[14px] text-muted">{{ [i.brand, i.code].filter(Boolean).join(' ') || t(`kinds.${i.kind}`) }}</span>
          </div>
          <span class="h-fit shrink-0 rounded-md bg-warn-bg px-2 py-0.5 text-xs font-semibold text-warn">{{ t('reorder.need', { n: need(i) }) }}</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="text-[15px]">{{ t('reorder.have', { have: i.quantity, min: i.min_quantity }) }}</span>
          <UIButton :loading="busy === i.id" @click="arrived(i)">{{ t('reorder.arrived', { n: need(i) }) }}</UIButton>
        </div>
      </article>
      <UIButton variant="outline" size="lg" block class="mt-2 md:w-auto md:justify-self-start lg:col-span-2" @click="share">
        <UIIcon name="upload" :size="20" />{{ t('reorder.share') }}
      </UIButton>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIEmpty, UIIcon } from '@kv/ui'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { type Item, useMove, useReorder } from '@/lib/queries'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const toast = useToast()
const { data, isPending, isError, error, refetch } = useReorder()
const { moveWithUndo } = useMove()
const items = computed(() => data.value?.items ?? [])
const need = (i: Item) => Math.max(i.min_quantity - i.quantity, 1)
const busy = ref<string | null>(null)

async function arrived(i: Item) {
  busy.value = i.id
  await moveWithUndo(i, { type: 'receipt', quantity: need(i) }, t('move.done.receipt', { n: need(i) }))
  busy.value = null
}

async function share() {
  const text = [t('reorder.shareTitle'), ...items.value.map((i) => {
    const code = [i.brand, i.code].filter(Boolean).join(' ')
    return `• ${i.name}${code ? ` (${code})` : ''} — ${need(i)} ${t('common.pcsShort')}`
  })].join('\n')
  try {
    if (navigator.share) await navigator.share({ text })
    else {
      await navigator.clipboard.writeText(text)
      toast.show(t('reorder.copied'))
    }
  } catch {
    /* cancelled */
  }
}
</script>
