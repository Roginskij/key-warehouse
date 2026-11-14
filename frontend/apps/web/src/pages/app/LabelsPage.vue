<template>
  <PageHeader class="print:hidden" :title="t('labels.title')" :subtitle="t('labels.subtitle')" :back="{ name: 'locations' }" :back-label="t('nav.locations')" />

  <div class="grid gap-4 p-3 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] print:block print:p-0">
    <!-- Settings: never printed -->
    <section class="flex flex-col gap-4 self-start rounded-card border border-line bg-surface p-4 print:hidden">
      <UISelect v-model="formatId" :label="t('labels.format')" :options="formatOptions" />
      <UIField v-model="skip" :label="t('labels.skip')" :hint="t('labels.skipHint')" inputmode="numeric" />
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[15px] font-semibold">{{ t('labels.which') }}</span>
          <span class="flex gap-3 text-[14px] font-semibold">
            <button type="button" class="underline" @click="selectAll(true)">{{ t('labels.all') }}</button>
            <button type="button" class="underline" @click="selectAll(false)">{{ t('labels.none') }}</button>
          </span>
        </div>
        <label v-for="l in locations" :key="l.id" class="flex items-center gap-3 rounded-control border border-line px-3 py-2">
          <input v-model="picked" type="checkbox" :value="l.id" class="size-5 shrink-0 accent-ink" />
          <span class="min-w-0 truncate">{{ places.get(l.id) }}</span>
        </label>
        <p v-if="!locations.length" class="m-0 text-muted">{{ t('locations.emptyText') }}</p>
      </div>
      <UIButton size="lg" :disabled="!labels.length" @click="print">
        <UIIcon name="printer" :size="20" />{{ t('labels.print', { n: labels.length }) }}
      </UIButton>
      <p class="m-0 text-[14px] text-muted">{{ t('labels.printHint') }}</p>
    </section>

    <!-- Preview = what is printed -->
    <!-- On screen the A4 sheet is shown smaller; printing uses real size. -->
    <div class="overflow-x-auto [zoom:0.45] sm:[zoom:0.6] lg:[zoom:0.7] print:overflow-visible print:[zoom:1]">
      <p v-if="!labels.length" class="m-0 rounded-card border border-line bg-surface p-6 text-center text-muted print:hidden">{{ t('labels.nothing') }}</p>
      <div
        v-for="(page, pi) in pages"
        :key="pi"
        class="sheet relative mb-4 bg-white shadow-sm print:mb-0 print:shadow-none"
        :style="{ width: '210mm', height: '297mm' }"
      >
        <div
          v-for="(cell, ci) in page"
          :key="ci"
          class="absolute flex items-center overflow-hidden"
          :class="cell ? 'outline-1 outline-dashed outline-line print:outline-none' : ''"
          :style="cellStyle(ci)"
        >
          <template v-if="cell">
            <div class="shrink-0 [&>svg]:block [&>svg]:size-full" :style="{ width: qrMm + 'mm', height: qrMm + 'mm' }" v-html="cell.svg" />
            <div class="flex min-w-0 flex-col justify-center" :style="{ paddingLeft: '2.5mm', gap: '0.8mm' }">
              <span class="font-bold leading-tight text-ink" :style="{ fontSize: format.titlePt + 'pt' }">{{ cell.name }}</span>
              <span v-if="cell.parent" class="leading-tight text-muted" :style="{ fontSize: format.smallPt + 'pt' }">{{ cell.parent }}</span>
              <span class="leading-tight text-muted" :style="{ fontSize: format.smallPt + 'pt' }">{{ session.workshop?.workshop_name }}</span>
              <span class="leading-tight font-semibold text-faint" :style="{ fontSize: format.smallPt - 1 + 'pt' }">KeyVerhaus</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/PageHeader.vue'
import { qrSvg, stickerUrl } from '@/lib/qr'
import { type Location, useLocationNames, useLocations } from '@/lib/queries'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const session = useSession()
const { data } = useLocations()
const places = useLocationNames()

/** Standard A4 label sheets (sizes in mm). */
const FORMATS = [
  { id: 'a4-21', cols: 3, rows: 7, w: 63.5, h: 38.1, top: 15.15, left: 7.2, gapX: 2.54, gapY: 0, titlePt: 11, smallPt: 7.5 },
  { id: 'a4-8', cols: 2, rows: 4, w: 99.1, h: 67.7, top: 13.1, left: 4.65, gapX: 2.5, gapY: 0, titlePt: 16, smallPt: 10 },
  { id: 'a4-65', cols: 5, rows: 13, w: 38.1, h: 21.2, top: 10.7, left: 4.75, gapX: 2.5, gapY: 0, titlePt: 7, smallPt: 5 },
] as const
const formatId = ref<string>(localStorage.getItem('kv.labelFormat') ?? 'a4-21')
watch(formatId, (v) => localStorage.setItem('kv.labelFormat', v))
const format = computed(() => FORMATS.find((f) => f.id === formatId.value) ?? FORMATS[0])
const formatOptions = computed(() => FORMATS.map((f) => ({ value: f.id, label: t(`labels.formats.${f.id.replace('-', '_')}`) })))
const qrMm = computed(() => Math.min(format.value.h - 4, format.value.w * 0.45))

const skip = ref('0')
const locations = computed<Location[]>(() => data.value ?? [])
const picked = ref<string[]>([])
watch(
  locations,
  (list) => {
    // Default: every place except the main one (that is the room itself).
    if (!picked.value.length) picked.value = list.filter((l) => !l.is_default).map((l) => l.id)
  },
  { immediate: true },
)
function selectAll(on: boolean) {
  picked.value = on ? locations.value.map((l) => l.id) : []
}

interface Cell { name: string; parent: string; svg: string }
const svgs = ref<Record<string, string>>({})
watch(
  picked,
  async (ids) => {
    for (const id of ids) {
      if (!svgs.value[id]) svgs.value = { ...svgs.value, [id]: await qrSvg(stickerUrl(session.wid, id)) }
    }
  },
  { immediate: true, deep: true },
)

const labels = computed<Cell[]>(() =>
  locations.value
    .filter((l) => picked.value.includes(l.id) && svgs.value[l.id])
    .map((l) => {
      const full = places.value.get(l.id) ?? l.name
      const parts = full.split(' › ')
      return { name: parts.pop() ?? full, parent: parts.join(' › '), svg: svgs.value[l.id] }
    }),
)
const pages = computed(() => {
  const per = format.value.cols * format.value.rows
  const skipN = Math.min(Math.max(0, Math.floor(Number(skip.value) || 0)), per - 1)
  const cells: (Cell | null)[] = [...Array(skipN).fill(null), ...labels.value]
  const out: (Cell | null)[][] = []
  for (let i = 0; i < cells.length; i += per) out.push(cells.slice(i, i + per))
  return out
})
function cellStyle(index: number) {
  const f = format.value
  const col = index % f.cols
  const row = Math.floor(index / f.cols)
  return {
    left: `${f.left + col * (f.w + f.gapX)}mm`,
    top: `${f.top + row * (f.h + f.gapY)}mm`,
    width: `${f.w}mm`,
    height: `${f.h}mm`,
    padding: '2mm 2.5mm',
    boxSizing: 'border-box' as const,
  }
}

function print() {
  window.print()
}
</script>
