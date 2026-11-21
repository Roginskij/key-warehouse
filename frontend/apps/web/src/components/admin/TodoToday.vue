<template>
  <section class="flex flex-col gap-3">
    <LoadError v-if="isError && !todo" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-40 animate-pulse rounded-card bg-surface" />
    <template v-else-if="todo">
      <div v-if="allDone" class="flex items-center gap-3 rounded-card border border-line bg-surface p-5">
        <span class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary"><UIIcon name="check" :size="22" /></span>
        <span class="flex flex-col">
          <b class="text-[17px]">{{ t('admin.todo.allDone') }}</b>
          <span class="text-[15px] text-muted">{{ t('admin.todo.allDoneHint') }}</span>
        </span>
      </div>

      <!-- 1. New codes from workshops -->
      <RouterLink
        v-if="todo.pending_proposals"
        :to="{ name: 'admin-proposals' }"
        class="flex items-center gap-3 rounded-card border-2 border-ink bg-primary-soft p-4 text-ink no-underline"
      >
        <span class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-[17px] font-bold">{{ todo.pending_proposals }}</span>
        <span class="flex min-w-0 flex-1 flex-col">
          <b class="text-[17px]">{{ t('admin.todo.proposals', { n: todo.pending_proposals }) }}</b>
          <span class="text-[14px] text-muted">{{ t('admin.todo.proposalsHint') }}</span>
        </span>
        <span :class="buttonClass('primary', 'md')" class="hidden sm:inline-flex">{{ t('admin.todo.review') }}</span>
        <UIIcon name="chevron" :size="22" class="sm:hidden" />
      </RouterLink>

      <!-- 2. In stock but not on the site -->
      <TodoTask
        v-if="todo.not_on_site.total"
        :count="todo.not_on_site.total"
        :title="t('admin.todo.notOnSite', { n: todo.not_on_site.total })"
        :hint="t('admin.todo.notOnSiteHint')"
        :more="moreLabel(todo.not_on_site)"
        @more="expanded = true"
      >
        <TodoItemRow v-for="i in todo.not_on_site.items" :key="i.id" :item="i" :action="t('admin.todo.addInfo')" />
      </TodoTask>

      <!-- 3. Look like the same key -->
      <TodoTask
        v-if="todo.duplicates.total"
        :count="todo.duplicates.total"
        :title="t('admin.todo.duplicates', { n: todo.duplicates.total })"
        :hint="t('admin.todo.duplicatesHint')"
        :more="moreLabel(todo.duplicates)"
        @more="expanded = true"
      >
        <div v-for="p in todo.duplicates.items" :key="p.a.id + p.b.id" class="flex flex-col gap-2 py-3">
          <span class="self-start rounded-md bg-ground px-2 py-0.5 text-[13px] font-semibold text-muted">{{ t(`admin.todo.reason.${p.reason}`) }}</span>
          <div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-center">
            <RouterLink :to="{ name: 'admin-item', params: { id: p.a.id } }" class="flex min-w-0 flex-col text-ink no-underline">
              <b class="truncate">{{ p.a.name }}</b><span class="truncate text-[14px] text-muted">{{ p.a.codes.join(' · ') }}</span>
            </RouterLink>
            <span class="hidden text-muted sm:block">↔</span>
            <RouterLink :to="{ name: 'admin-item', params: { id: p.b.id } }" class="flex min-w-0 flex-col text-ink no-underline">
              <b class="truncate">{{ p.b.name }}</b><span class="truncate text-[14px] text-muted">{{ p.b.codes.join(' · ') }}</span>
            </RouterLink>
          </div>
          <div v-if="canEdit" class="flex flex-wrap gap-2">
            <UIButton size="sm" @click="merging = p">{{ t('admin.todo.same') }}</UIButton>
            <UIButton size="sm" variant="outline" @click="dismiss(p)">{{ t('admin.todo.different') }}</UIButton>
          </div>
        </div>
      </TodoTask>

      <!-- 4. On the site without a photo -->
      <TodoTask
        v-if="todo.no_photo.total"
        :count="todo.no_photo.total"
        :title="t('admin.todo.noPhoto', { n: todo.no_photo.total })"
        :hint="t('admin.todo.noPhotoHint')"
        :more="moreLabel(todo.no_photo)"
        quiet
        @more="expanded = true"
      >
        <TodoItemRow v-for="i in todo.no_photo.items" :key="i.id" :item="i" :action="t('admin.todo.addPhoto')" />
      </TodoTask>
    </template>
  </section>

  <Sheet :open="!!merging" :title="t('admin.todo.mergeTitle')" :close-label="t('common.close')" @close="merging = null">
    <template v-if="merging">
      <p class="m-0">{{ t('admin.todo.mergeText') }}</p>
      <label v-for="side in [merging.a, merging.b]" :key="side.id" class="flex items-start gap-3 rounded-control border border-line p-3">
        <input v-model="mainId" type="radio" :value="side.id" class="mt-1 size-5 shrink-0 accent-ink" />
        <span class="flex min-w-0 flex-col">
          <b>{{ side.name }}</b>
          <span class="text-[14px] text-muted">{{ side.codes.join(' · ') }}</span>
          <span class="text-[13px] text-muted">{{ t('admin.todo.inWorkshops', { n: side.workshops }) }}</span>
        </span>
      </label>
      <UIButton size="lg" block :disabled="!mainId" @click="merge">{{ t('admin.todo.mergeButton') }}</UIButton>
    </template>
  </Sheet>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { buttonClass, UIButton, UIIcon } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import TodoItemRow from '@/components/admin/TodoItemRow.vue'
import TodoTask from '@/components/admin/TodoTask.vue'
import LoadError from '@/components/LoadError.vue'
import Sheet from '@/components/Sheet.vue'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

type Pair = Schemas['DuplicatePair']

const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const canEdit = computed(() => session.can('catalog.edit'))

const expanded = ref(false)
const { data: todo, isPending, isError, error, refetch } = useQuery({
  queryKey: computed(() => ['admin-todo', expanded.value]),
  queryFn: () => call(client.GET('/api/v1/admin/todo', { params: { query: { limit: expanded.value ? 200 : 5 } } })),
  placeholderData: (prev) => prev,
})
const allDone = computed(
  () => !!todo.value && !todo.value.pending_proposals && !todo.value.not_on_site.total && !todo.value.duplicates.total && !todo.value.no_photo.total,
)
const moreLabel = (l: { total: number; items: unknown[] }) => (l.total > l.items.length ? t('admin.todo.showAll', { n: l.total }) : '')

function refresh() {
  qc.invalidateQueries({ queryKey: ['admin-todo'] })
  qc.invalidateQueries({ queryKey: ['admin-catalog'] })
}

// --- duplicates
const merging = ref<Pair | null>(null)
const mainId = ref('')
// The card more workshops already use stays the main one by default.
watch(merging, (p) => (mainId.value = p ? (p.a.workshops >= p.b.workshops ? p.a.id : p.b.id) : ''))
async function merge() {
  const p = merging.value
  if (!p || !mainId.value) return
  const other = mainId.value === p.a.id ? p.b : p.a
  try {
    await call(
      client.POST('/api/v1/admin/catalog/items/{item_id}/merge', {
        params: { path: { item_id: mainId.value } },
        body: { source_item_ids: [other.id] },
      }),
    )
    merging.value = null
    toast.show(t('admin.item.merged', { name: other.name }))
    refresh()
  } catch (e) {
    toast.error(errorText(e))
  }
}
async function dismiss(p: Pair) {
  try {
    await call(client.POST('/api/v1/admin/todo/duplicates/dismiss', { body: { item_ids: [p.a.id, p.b.id] } }))
    toast.show(t('admin.todo.dismissed'))
    refresh()
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
