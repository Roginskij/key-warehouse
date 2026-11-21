<template>
  <PageHeader :title="item?.name ?? '…'" :subtitle="item?.my_name ?? undefined" :back="{ name: 'stock' }" :back-label="t('nav.stock')">
    <template #actions>
      <RouterLink
        v-if="item"
        :to="{ name: 'item-edit', params: { id } }"
        :class="buttonClass('on-graphite', 'md')"
        class="md:border md:border-line-strong md:bg-surface md:text-ink"
      >
        <UIIcon name="edit" :size="18" />{{ t('common.edit') }}
      </RouterLink>
    </template>
  </PageHeader>

  <div v-if="isError && !item" class="p-3 md:p-0"><LoadError :error="error" @retry="refetch()" /></div>
  <div v-else-if="isPending" class="m-3 h-40 animate-pulse rounded-card bg-surface" />

  <div v-else-if="item" class="grid gap-3 p-3 md:p-0 md:pb-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-5">
    <div class="flex flex-col gap-3">
      <section class="flex items-center gap-4 rounded-card border border-line bg-surface p-4">
        <label class="relative flex size-24 shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded-[14px] border-2 border-dashed border-line-strong bg-ground text-muted">
          <img v-if="photoUrl" :src="photoUrl" :alt="item.name" class="size-full object-cover" />
          <span v-else class="flex flex-col items-center gap-1 text-[13px] font-semibold">
            <UIIcon name="camera" :size="28" />{{ uploading ? '…' : t('item.photo') }}
          </span>
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" class="sr-only" @change="onPhoto" />
        </label>
        <div class="flex min-w-0 flex-col gap-2">
          <span class="text-[14px] text-muted">{{ t(`kinds.${item.kind}`) }}</span>
          <div v-if="codes.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="c in codes"
              :key="c.label"
              class="rounded-md px-2 py-0.5 text-[14px] font-semibold"
              :class="c.own ? 'bg-primary-soft text-ink' : 'bg-ground text-ink'"
            >{{ c.label }}</span>
          </div>
          <span v-if="item.vehicles" class="text-[14px] text-muted">{{ t('item.fits', { cars: item.vehicles }) }}</span>
          <AttributesView :kind="item.kind" :values="item.attributes" class="mt-1" />
          <span v-if="item.catalog_status === 'linked'" class="text-[13px] text-faint">{{ t('item.fromCatalog') }}</span>
          <span v-else-if="item.catalog_status === 'pending'" class="self-start rounded-md bg-primary-soft px-2 py-0.5 text-[13px] font-semibold">{{ t('item.review.pending') }}</span>
          <span v-else-if="item.catalog_status === 'rejected'" class="self-start rounded-md bg-warn-bg px-2 py-0.5 text-[13px] font-semibold text-warn">{{ t('item.review.rejected') }}</span>
        </div>
      </section>

      <section class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4">
        <div class="flex items-center justify-between">
          <div class="flex flex-col">
            <span class="text-[15px] text-muted">{{ t('item.inStock') }}</span>
            <span v-if="item.min_quantity" class="text-[14px]" :class="item.needs_reorder ? 'font-semibold text-warn' : 'text-muted'">
              {{ t('item.minimum', { n: item.min_quantity }) }}
            </span>
          </div>
          <span class="text-[32px] leading-none font-bold tabular-nums" :class="item.needs_reorder ? 'text-warn' : 'text-ink'">
            {{ t('common.pcs', { n: item.quantity }) }}
          </span>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <UIButton variant="dark" :disabled="!item.quantity" @click="sheet = 'sale'">{{ t('move.short.sale') }}</UIButton>
          <UIButton variant="outline" @click="sheet = 'receipt'">{{ t('move.short.receipt') }}</UIButton>
          <UIButton variant="outline" :disabled="!item.quantity" @click="sheet = 'writeoff'">{{ t('move.short.writeoff') }}</UIButton>
        </div>
        <button
          v-if="item.quantity && places.size > 1"
          type="button"
          class="self-start text-[15px] font-semibold underline"
          @click="sheet = 'transfer'"
        >{{ t('move.short.transfer') }}</button>
      </section>
    </div>

    <div class="flex flex-col gap-3">
      <section class="rounded-card border border-line bg-surface px-4 py-1">
        <dl class="m-0 divide-y divide-ground">
          <div class="flex min-h-12 items-center justify-between gap-3">
            <dt class="text-muted">{{ t('item.salePrice') }}</dt>
            <dd class="m-0 text-[17px] font-bold">{{ money(item.sale_price, item.sale_currency) }}</dd>
          </div>
          <div v-if="item.cut_price" class="flex min-h-12 items-center justify-between gap-3">
            <dt class="text-muted">{{ t('item.cutPrice') }}</dt>
            <dd class="m-0 text-[17px] font-bold">{{ money(item.cut_price, item.cut_currency) }}</dd>
          </div>
          <div v-for="lv in item.levels" :key="lv.location_id" class="flex min-h-12 items-center justify-between gap-3">
            <dt class="text-muted">{{ places.get(lv.location_id) ?? '…' }}</dt>
            <dd class="m-0 font-semibold">{{ t('common.pcs', { n: lv.quantity }) }}</dd>
          </div>
        </dl>
      </section>
      <p v-if="item.notes" class="m-0 rounded-card border border-line bg-surface p-4 whitespace-pre-line">{{ item.notes }}</p>

      <section class="flex flex-col gap-2 px-1">
        <h2 class="m-0 text-[16px] font-bold">{{ t('item.history') }}</h2>
        <p v-if="!history.data.value?.items.length" class="m-0 text-muted">{{ t('item.noHistory') }}</p>
        <ul class="m-0 flex list-none flex-col gap-1.5 p-0">
          <li v-for="m in history.data.value?.items" :key="m.id" class="text-[15px] text-ink">
            <span class="text-muted">{{ dateTime(m.created_at) }} · {{ m.user_name }} ·</span>
            {{ typeLabel(m.type) }} {{ m.quantity > 0 && m.type !== 'transfer' ? '+' : '' }}{{ m.quantity }}
            <span v-if="m.unit_price && m.type === 'sale'" class="text-muted">· {{ money(m.unit_price, m.currency) }}</span>
            <span v-if="m.client_name" class="text-muted">· {{ m.client_name }}</span>
          </li>
        </ul>
      </section>

      <UIButton v-if="!item.quantity" variant="danger" class="self-start" @click="archive">
        <UIIcon name="trash" :size="18" />{{ t('item.archive') }}
      </UIButton>
    </div>

    <MoveSheet
      v-if="sheet"
      :open="!!sheet"
      :kind="sheet"
      :item="item"
      @close="sheet = null"
      @submit="submitMove"
    />
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIIcon } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import LoadError from '@/components/LoadError.vue'
import AttributesView from '@/components/AttributesView.vue'
import PageHeader from '@/components/PageHeader.vue'
import MoveSheet, { type MoveKind } from '@/components/stock/MoveSheet.vue'
import { call, client, raw } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { dateTime, money } from '@/lib/format'
import { useItem, useLocationNames, useMove, type MovementBody } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const router = useRouter()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const places = useLocationNames()
const { data: item, isPending, isError, error, refetch } = useItem(() => props.id)
const { moveWithUndo } = useMove()

const history = useQuery({
  queryKey: computed(() => ['movements', session.wid, props.id]),
  queryFn: () =>
    call(
      client.GET('/api/v1/workshops/{workshop_id}/inventory/movements', {
        params: { path: { workshop_id: session.wid }, query: { item_id: props.id, limit: 8 } },
      }),
    ),
})

const codes = computed(() => {
  if (!item.value) return []
  const out: { label: string; own: boolean }[] = []
  if (item.value.code) out.push({ label: [item.value.brand, item.value.code].filter(Boolean).join(' '), own: true })
  for (const c of item.value.catalog_item?.codes ?? []) {
    const label = `${c.brand} ${c.code}`
    if (!out.some((o) => o.label.toLowerCase() === label.toLowerCase())) out.push({ label, own: false })
  }
  return out
})

// Photo: the endpoint needs the auth header, so load it as a blob.
const photoUrl = ref<string | null>(null)
watch(
  () => [item.value?.id, item.value?.has_photo, item.value?.updated_at],
  async () => {
    if (photoUrl.value) URL.revokeObjectURL(photoUrl.value)
    photoUrl.value = null
    if (!item.value?.has_photo) return
    try {
      const res = await raw(`/api/v1/workshops/${session.wid}/inventory/items/${item.value.id}/photo`)
      photoUrl.value = URL.createObjectURL(await res.blob())
    } catch {
      /* no photo */
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => photoUrl.value && URL.revokeObjectURL(photoUrl.value))

const uploading = ref(false)
async function onPhoto(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !item.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await raw(`/api/v1/workshops/${session.wid}/inventory/items/${item.value.id}/photo`, { method: 'PUT', body: fd })
    qc.setQueryData(['item', session.wid, item.value.id], await res.json())
  } catch (err) {
    toast.error(errorText(err))
  } finally {
    uploading.value = false
  }
}

const sheet = ref<MoveKind | null>(null)
async function submitMove(body: MovementBody) {
  if (!item.value) return
  const kind = sheet.value!
  sheet.value = null
  await moveWithUndo(item.value, body, t(`move.done.${kind}`, { n: body.quantity }))
}

async function archive() {
  if (!item.value) return
  try {
    await call(
      client.DELETE('/api/v1/workshops/{workshop_id}/inventory/items/{item_id}', {
        params: { path: { workshop_id: session.wid, item_id: item.value.id } },
      }),
    )
    qc.invalidateQueries({ queryKey: ['items', session.wid] })
    toast.show(t('item.archived'))
    router.replace({ name: 'stock' })
  } catch (e) {
    toast.error(errorText(e))
  }
}

const typeLabel = (type: string) => t(`move.type.${type}`)
</script>
