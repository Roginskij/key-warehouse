<template>
  <PageHeader :title="t('admin.proposals.title')" :subtitle="t('admin.proposals.subtitle')">
    <div class="flex flex-wrap gap-2">
      <select v-model="status" :aria-label="t('admin.catalog.status')" class="h-11 rounded-control border-2 border-graphite-2 bg-graphite-2 px-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink">
        <option v-for="s in ['pending', 'accepted', 'rejected']" :key="s" :value="s">{{ t(`admin.proposals.status.${s}`) }}</option>
      </select>
      <select v-model="type" :aria-label="t('admin.proposals.type')" class="h-11 rounded-control border-2 border-graphite-2 bg-graphite-2 px-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink">
        <option value="">{{ t('admin.proposals.allTypes') }}</option>
        <option v-for="ty in ['new_item', 'equivalent', 'substitute', 'add_code']" :key="ty" :value="ty">{{ t(`admin.proposals.types.${ty}`) }}</option>
      </select>
    </div>
  </PageHeader>

  <div class="grid content-start gap-3 p-3 md:p-0 md:pb-12 lg:grid-cols-2">
    <LoadError v-if="isError && !data" class="lg:col-span-2" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-32 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!data?.items.length" class="lg:col-span-2" icon="check" :title="t('admin.proposals.empty')" />
    <article v-for="p in data?.items" :key="p.id" class="flex flex-col gap-3 rounded-[14px] border border-line bg-surface p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="flex min-w-0 flex-col gap-1">
          <span class="text-[13px] font-semibold text-muted">{{ t(`admin.proposals.types.${p.type}`) }} · {{ dateTime(p.created_at) }}</span>
          <span class="font-semibold">{{ describe(p).title }}</span>
          <span class="text-[14px] text-muted">{{ describe(p).detail }}</span>
        </div>
        <span class="shrink-0 rounded-md bg-primary-soft px-2 py-0.5 text-[13px] font-bold">{{ t('admin.proposals.votes', { n: p.votes_count }) }}</span>
      </div>
      <p v-if="p.decision_note" class="m-0 text-[14px] text-muted">{{ p.decision_note }}</p>
      <div class="flex flex-wrap gap-2">
        <template v-if="p.status === 'pending' && canModerate">
          <UIButton size="sm" @click="startAccept(p)">{{ t('admin.proposals.accept') }}</UIButton>
          <UIButton size="sm" variant="outline" @click="rejecting = p">{{ t('admin.proposals.reject') }}</UIButton>
        </template>
        <RouterLink v-if="p.result_item_id" :to="{ name: 'admin-item', params: { id: p.result_item_id } }" class="self-center text-[15px] font-semibold text-ink">{{ t('admin.item.open') }}</RouterLink>
      </div>
    </article>
  </div>

  <Sheet :open="!!accepting" :title="t('admin.proposals.acceptTitle')" :close-label="t('common.close')" @close="accepting = null">
    <form class="flex flex-col gap-4" @submit.prevent="accepting && accept(accepting, { kind: acceptKind as never, name: acceptName.trim() || null })">
      <p class="m-0 text-[15px] text-muted">{{ t('admin.proposals.acceptHint') }}</p>
      <UISelect v-model="acceptKind" :label="t('item.form.kind')" :options="kindOptions" />
      <UIField v-model="acceptName" :label="t('item.form.name')" />
      <UIButton type="submit" size="lg" block>{{ t('admin.proposals.accept') }}</UIButton>
    </form>
  </Sheet>
  <Sheet :open="!!rejecting" :title="t('admin.proposals.reject')" :close-label="t('common.close')" @close="rejecting = null">
    <form class="flex flex-col gap-4" @submit.prevent="reject">
      <UIField v-model="note" :label="t('admin.proposals.reason')" :hint="t('move.optional')" />
      <UIButton type="submit" variant="dark" size="lg" block>{{ t('admin.proposals.reject') }}</UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIEmpty, UIField, UISelect } from '@kv/ui'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import Sheet from '@/components/Sheet.vue'
import { KINDS } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { dateTime } from '@/lib/format'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

type P = Schemas['ProposalOut']
type Ref = { brand: string; code: string }
const { t } = useI18n()
const router = useRouter()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const canModerate = computed(() => session.can('catalog.moderate'))

const status = ref<'pending' | 'accepted' | 'rejected'>('pending')
const type = ref('')
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: computed(() => ['admin-proposals', status.value, type.value]),
  queryFn: () =>
    call(client.GET('/api/v1/admin/catalog/proposals', { params: { query: { status: status.value, type: (type.value || undefined) as never, limit: 100 } } })),
  placeholderData: keepPreviousData,
})

const code = (r?: Ref) => (r ? `${r.brand} ${r.code}` : '')
function describe(p: P) {
  const d = p.payload as Record<string, any>
  switch (p.type) {
    case 'new_item':
      return { title: t('admin.proposals.newItem', { name: d.name }), detail: `${t(`kinds.${d.kind}`)} · ${(d.codes as Ref[]).map(code).join(' · ')}` }
    case 'equivalent':
      return { title: t('admin.proposals.equivalent', { a: code(d.a), b: code(d.b) }), detail: t('admin.proposals.equivalentHint') }
    case 'substitute':
      return { title: t('admin.proposals.substitute', { sub: code(d.substitute), item: code(d.item) }), detail: d.note ?? t('admin.proposals.substituteHint') }
    default:
      return { title: t('admin.proposals.addCode', { code: code(d.code) }), detail: t('admin.proposals.addCodeHint') }
  }
}

const accepting = ref<P | null>(null)
const acceptKind = ref('')
const acceptName = ref('')
const needsDetails = (p: P) => p.type === 'new_item' || p.type === 'equivalent'
function startAccept(p: P) {
  if (!needsDetails(p)) return accept(p)
  const d = p.payload as Record<string, any>
  accepting.value = p
  acceptKind.value = d.kind ?? 'blank'
  acceptName.value = d.name ?? d.a?.code ?? ''
}
async function accept(p: P, body?: Schemas['ProposalAcceptIn']) {
  try {
    const item = await call(client.POST('/api/v1/admin/catalog/proposals/{proposal_id}/accept', { params: { path: { proposal_id: p.id } }, body }))
    accepting.value = null
    refresh()
    toast.show(t('admin.proposals.accepted'), {
      action: { label: t('admin.item.open'), run: () => void router.push({ name: 'admin-item', params: { id: item.id } }) },
    })
  } catch (e) {
    toast.error(errorText(e))
  }
}

const rejecting = ref<P | null>(null)
const note = ref('')
async function reject() {
  if (!rejecting.value) return
  try {
    await call(client.POST('/api/v1/admin/catalog/proposals/{proposal_id}/reject', { params: { path: { proposal_id: rejecting.value.id } }, body: { note: note.value || null } }))
    rejecting.value = null
    note.value = ''
    refresh()
  } catch (e) {
    toast.error(errorText(e))
  }
}
function refresh() {
  qc.invalidateQueries({ queryKey: ['admin-proposals'] })
  qc.invalidateQueries({ queryKey: ['admin-pending-count'] })
  qc.invalidateQueries({ queryKey: ['admin-catalog'] })
}
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) })))
</script>
