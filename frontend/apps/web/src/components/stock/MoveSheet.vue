<template>
  <Sheet :open="open" :title="t(`move.title.${kind}`)" :close-label="t('common.close')" @close="emit('close')">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <UIField v-model="qty" :label="t('move.quantity')" inputmode="numeric" />
      <UISelect v-if="showFrom" v-model="from" :label="t('move.from')" :options="fromOptions" />
      <UISelect v-if="kind === 'receipt' || kind === 'transfer'" v-model="to" :label="t('move.to')" :options="locOptions" />
      <template v-if="kind === 'sale'">
        <UIField v-model="price" :label="t('move.price', { cur: item.sale_currency ?? '' })" inputmode="decimal" />
        <details class="rounded-control border border-line px-3 py-2">
          <summary class="cursor-pointer py-1 text-[15px] font-semibold">{{ t('move.client') }}</summary>
          <div class="flex flex-col gap-3 pt-3">
            <UIField v-model="client" :label="t('move.clientName')" autocomplete="off" />
            <UIField v-model="phone" :label="t('move.clientPhone')" type="tel" inputmode="tel" autocomplete="off" />
          </div>
        </details>
      </template>
      <UIField v-if="kind === 'writeoff'" v-model="note" :label="t('move.reason')" :placeholder="t('move.reasonPlaceholder')" />
      <UIButton type="submit" size="lg" block>{{ t(`move.confirm.${kind}`) }}</UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import { UIButton, UIField, UISelect } from '@kv/ui'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Sheet from '@/components/Sheet.vue'
import type { Item, MovementBody } from '@/lib/queries'
import { useLocationNames } from '@/lib/queries'

export type MoveKind = 'sale' | 'receipt' | 'writeoff' | 'transfer'

const props = defineProps<{ open: boolean; kind: MoveKind; item: Item }>()
const emit = defineEmits<{ close: []; submit: [MovementBody] }>()
const { t } = useI18n()
const places = useLocationNames()

const qty = ref('1')
const price = ref('')
const client = ref('')
const phone = ref('')
const note = ref('')
const from = ref<string | null>(null)
const to = ref<string | null>(null)

watch(
  () => props.open,
  (v) => {
    if (!v) return
    qty.value = '1'
    price.value = props.kind === 'sale' ? (props.item.sale_price ?? '') : ''
    client.value = phone.value = note.value = ''
    const stocked = [...props.item.levels].sort((a, b) => b.quantity - a.quantity)
    from.value = stocked[0]?.location_id ?? null
    to.value =
      props.kind === 'receipt'
        ? (stocked[0]?.location_id ?? [...places.value.keys()][0] ?? null)
        : ([...places.value.keys()].find((id) => id !== from.value) ?? null)
  },
  { immediate: true },
)

const locOptions = computed(() => [...places.value].map(([value, label]) => ({ value, label })))
const fromOptions = computed(() =>
  props.item.levels.map((lv: Item['levels'][number]) => ({ value: lv.location_id, label: `${places.value.get(lv.location_id) ?? '?'} (${lv.quantity})` })),
)
const showFrom = computed(() => props.kind === 'transfer' || (props.kind !== 'receipt' && props.item.levels.length > 1))

function submit() {
  const quantity = Math.max(1, Math.round(Number(qty.value.replace(',', '.')) || 1))
  const body: MovementBody = { type: props.kind, quantity }
  if (props.kind === 'receipt') body.location_id = to.value
  else if (showFrom.value) body.location_id = from.value
  if (props.kind === 'transfer') body.to_location_id = to.value
  if (props.kind === 'sale') {
    if (price.value) body.unit_price = price.value.replace(',', '.')
    if (client.value) body.client_name = client.value
    if (phone.value) body.client_phone = phone.value
  }
  if (note.value) body.note = note.value
  emit('submit', body)
}
</script>
