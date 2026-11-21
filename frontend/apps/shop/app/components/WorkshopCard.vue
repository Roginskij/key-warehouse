<template>
  <article class="flex flex-col gap-3 rounded-card border bg-surface p-4" :class="w.in_stock ? 'border-ink' : 'border-line'">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex min-w-0 flex-col gap-0.5">
        <h3 class="m-0 text-[17px] font-bold">
          {{ w.name }}
          <span v-if="w.verified" class="ml-1 rounded-md bg-primary-soft px-1.5 py-px align-middle text-xs font-bold">✓ {{ t('key.verified') }}</span>
        </h3>
        <span class="text-[14px] text-muted">{{ [w.city, w.address].filter(Boolean).join(', ') }}</span>
        <span v-if="w.hours" class="text-[14px] text-muted">{{ t('key.hours') }}: {{ w.hours }}</span>
      </div>
      <div v-if="showStock && w.in_stock" class="flex flex-col items-end gap-0.5">
        <span class="rounded-md bg-primary px-2 py-0.5 text-[13px] font-bold text-on-primary">{{ t('key.inStock') }}</span>
        <!-- No price shown: "ask for the price". Otherwise the blank and the work, each if set. -->
        <span v-if="!w.price && !w.cut_price" class="text-[15px] font-semibold">{{ t('key.priceAsk') }}</span>
        <span v-if="w.price" class="text-[15px]">{{ t('key.priceBlank') }}: <b>{{ priceText(w.price) }}</b></span>
        <span v-if="w.cut_price" class="text-[15px]">{{ t('key.priceCut') }}: <b>{{ priceText(w.cut_price) }}</b></span>
      </div>
    </div>
    <p v-if="w.about" class="m-0 text-[15px]">{{ w.about }}</p>
    <div class="flex flex-wrap gap-2">
      <a v-if="w.phone" :href="`tel:${w.phone.replace(/[^\d+]/g, '')}`" :class="buttonClass('primary', 'md')" @click="trackClick(w.id, 'phone', keySlug)">
        <UIIcon name="phone" :size="18" />{{ t('key.call') }}
      </a>
      <a v-if="w.viber" :href="`viber://chat?number=${encodeURIComponent(w.viber.replace(/[^\d+]/g, ''))}`" :class="buttonClass('outline', 'md')" @click="trackClick(w.id, 'viber', keySlug)">Viber</a>
      <a v-if="w.telegram" :href="`https://t.me/${w.telegram.replace(/^@/, '')}`" target="_blank" rel="noopener nofollow" :class="buttonClass('outline', 'md')" @click="trackClick(w.id, 'telegram', keySlug)">Telegram</a>
      <a v-if="mapUrl" :href="mapUrl" target="_blank" rel="noopener nofollow" :class="buttonClass('ghost', 'md')" @click="trackClick(w.id, 'route', keySlug)">
        <UIIcon name="pin" :size="18" />{{ t('key.route') }}
      </a>
    </div>
  </article>
</template>

<script setup lang="ts">
import { buttonClass, UIIcon } from '@kv/ui'

const props = defineProps<{ w: PublicWorkshop; keySlug?: string; showStock?: boolean }>()
const { t, lang } = useLang()

function priceText(p: { mode: string; amount: string; currency: string }) {
  const money = new Intl.NumberFormat(lang.value, { style: 'currency', currency: p.currency, maximumFractionDigits: 0 }).format(Number(p.amount))
  return p.mode === 'from' ? t('key.priceFrom', { price: money }) : money
}
// OpenStreetMap: no Google tracking; coordinates if given, otherwise the address.
const mapUrl = computed(() => {
  const w = props.w
  if (w.lat && w.lng) return `https://www.openstreetmap.org/?mlat=${w.lat}&mlon=${w.lng}#map=17/${w.lat}/${w.lng}`
  const q = [w.address, w.city].filter(Boolean).join(', ')
  return q ? `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}` : ''
})
</script>
