<template>
  <!-- Cars -->
  <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
    <h2 class="m-0 text-[17px] font-bold">{{ t('admin.fits.vehicles') }}</h2>
    <p v-if="!item.vehicle_fits.length" class="m-0 text-[15px] text-muted">—</p>
    <div v-for="f in item.vehicle_fits" :key="f.id" class="flex items-center gap-2">
      <span class="min-w-0 flex-1">
        <b>{{ f.make }} {{ f.model }}</b>
        <span class="text-muted"> {{ years(f.year_from, f.year_to) }}<template v-if="f.note"> · {{ f.note }}</template></span>
      </span>
      <button v-if="canEdit" type="button" class="flex size-9 items-center justify-center rounded-full text-danger hover:bg-danger-bg" :aria-label="t('common.delete')" @click="removeFit('vehicle', f.id)"><UIIcon name="close" :size="18" /></button>
    </div>
    <form v-if="editable" class="grid grid-cols-2 gap-2 border-t border-ground pt-3 sm:grid-cols-[1fr_1fr_5rem_5rem_auto]" @submit.prevent="addVehicle">
      <input v-model="car.make" :placeholder="t('admin.fits.make')" :aria-label="t('admin.fits.make')" :class="input" />
      <input v-model="car.model" :placeholder="t('admin.fits.model')" :aria-label="t('admin.fits.model')" :class="input" />
      <input v-model="car.year_from" :placeholder="t('admin.fits.from')" :aria-label="t('admin.fits.from')" inputmode="numeric" :class="input" />
      <input v-model="car.year_to" :placeholder="t('admin.fits.to')" :aria-label="t('admin.fits.to')" inputmode="numeric" :class="input" />
      <UIButton type="submit" class="col-span-2 sm:col-span-1">{{ t('admin.item.add') }}</UIButton>
    </form>
  </section>

  <!-- Locks and doors -->
  <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
    <h2 class="m-0 text-[17px] font-bold">{{ t('admin.fits.locks') }}</h2>
    <p class="m-0 text-[14px] text-muted">{{ t('admin.fits.locksHint') }}</p>
    <p v-if="!item.lock_fits.length" class="m-0 text-[15px] text-muted">—</p>
    <div v-for="f in item.lock_fits" :key="f.id" class="flex items-center gap-2">
      <span class="min-w-0 flex-1">
        <b>{{ f.make }} {{ f.model }}</b>
        <span class="text-muted"><template v-if="f.profile"> · {{ f.profile }}</template><template v-if="f.note"> · {{ f.note }}</template></span>
      </span>
      <button v-if="canEdit" type="button" class="flex size-9 items-center justify-center rounded-full text-danger hover:bg-danger-bg" :aria-label="t('common.delete')" @click="removeFit('lock', f.id)"><UIIcon name="close" :size="18" /></button>
    </div>
    <form v-if="editable" class="grid grid-cols-2 gap-2 border-t border-ground pt-3 sm:grid-cols-[1fr_1fr_8rem_auto]" @submit.prevent="addLock">
      <input v-model="lock.make" :placeholder="t('admin.fits.lockMake')" :aria-label="t('admin.fits.lockMake')" :class="input" />
      <input v-model="lock.model" :placeholder="t('admin.fits.lockModel')" :aria-label="t('admin.fits.lockModel')" :class="input" />
      <input v-model="lock.profile" :placeholder="t('admin.fits.profile')" :aria-label="t('admin.fits.profile')" :class="input" />
      <UIButton type="submit">{{ t('admin.item.add') }}</UIButton>
    </form>
  </section>

  <!-- Photos -->
  <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
    <h2 class="m-0 text-[17px] font-bold">{{ t('admin.photos.title') }}</h2>
    <p class="m-0 text-[14px] text-muted">{{ t('admin.photos.hint') }}</p>
    <div v-if="item.images.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <figure v-for="img in item.images" :key="img.id" class="m-0 flex flex-col gap-1">
        <img :src="img.url" :alt="item.name" class="aspect-square w-full rounded-control border border-line bg-ground object-contain" loading="lazy" />
        <figcaption class="text-[13px] text-muted">
          <b v-if="img.is_primary" class="text-ink">{{ t('admin.photos.primary') }} · </b>{{ t(`admin.photos.sources.${img.source_type}`) }}<template v-if="img.source_note"> · {{ img.source_note }}</template>
        </figcaption>
        <div v-if="canEdit" class="flex gap-1">
          <UIButton v-if="!img.is_primary" size="sm" variant="ghost" @click="makePrimary(img.id)">{{ t('admin.photos.makePrimary') }}</UIButton>
          <UIButton size="sm" variant="danger" @click="removeImage(img.id)">{{ t('common.delete') }}</UIButton>
        </div>
      </figure>
    </div>
    <form v-if="editable" class="flex flex-col gap-3 border-t border-ground pt-3" @submit.prevent="upload">
      <UISelect v-model="photo.source_type" :label="t('admin.photos.source')" :options="sourceOptions" />
      <UIField v-model="photo.source_note" :label="t('admin.photos.note')" :hint="t('admin.photos.noteHint')" />
      <label class="flex flex-col gap-1.5">
        <span class="text-[15px] font-semibold">{{ t('admin.photos.file') }}</span>
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="text-[15px]" />
      </label>
      <label class="flex items-start gap-3 text-[14px]">
        <input v-model="photo.rights" type="checkbox" class="mt-0.5 size-5 shrink-0 accent-ink" />{{ t('admin.photos.rights') }}
      </label>
      <UIButton type="submit" :loading="uploading" :disabled="!photo.rights" class="self-start">{{ t('admin.photos.upload') }}</UIButton>
    </form>
  </section>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { call, client, raw } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useToast } from '@/stores/toast'

type Detail = Schemas['ItemAdminDetailOut']
const props = defineProps<{ item: Detail; canEdit: boolean }>()
const emit = defineEmits<{ updated: [Detail] }>()
const { t } = useI18n()
const toast = useToast()

const editable = computed(() => props.canEdit && props.item.status === 'active')
const input = 'h-11 min-w-0 rounded-control border-2 border-line-strong px-3 outline-none focus:border-ink'
const path = computed(() => ({ item_id: props.item.id }))

async function act(fn: () => Promise<Detail>) {
  try {
    emit('updated', await fn())
    return true
  } catch (e) {
    toast.error(errorText(e))
    return false
  }
}
const year = (v: string) => (v.trim() ? Number(v.trim()) : null)
const years = (a?: number | null, b?: number | null) => (a || b ? `${a ?? '…'}–${b ?? '…'}` : '')

const car = ref({ make: '', model: '', year_from: '', year_to: '' })
async function addVehicle() {
  const c = car.value
  if (!c.make.trim() || !c.model.trim()) return
  const ok = await act(() =>
    call(
      client.POST('/api/v1/admin/catalog/items/{item_id}/fits/vehicle', {
        params: { path: path.value },
        body: { make: c.make.trim(), model: c.model.trim(), year_from: year(c.year_from), year_to: year(c.year_to) },
      }),
    ),
  )
  if (ok) car.value = { make: c.make, model: '', year_from: '', year_to: '' }
}

const lock = ref({ make: '', model: '', profile: '' })
async function addLock() {
  const l = lock.value
  if (!l.make.trim() || !l.model.trim()) return
  const ok = await act(() =>
    call(
      client.POST('/api/v1/admin/catalog/items/{item_id}/fits/lock', {
        params: { path: path.value },
        body: { make: l.make.trim(), model: l.model.trim(), profile: l.profile.trim() || null },
      }),
    ),
  )
  if (ok) lock.value = { make: l.make, model: '', profile: l.profile }
}

function removeFit(kind: 'vehicle' | 'lock', fitId: string) {
  return act(() => call(client.DELETE('/api/v1/admin/catalog/fits/{kind}/{fit_id}', { params: { path: { kind, fit_id: fitId } } })))
}

// --- photos: every photo records where it came from (own / workshop / supplier with permission)
const sourceOptions = computed(() => (['own', 'workshop', 'supplier'] as const).map((v) => ({ value: v, label: t(`admin.photos.sources.${v}`) })))
const photo = ref({ source_type: 'own', source_note: '', rights: false })
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
async function upload() {
  const file = fileInput.value?.files?.[0]
  if (!file) return toast.error(t('admin.photos.pick'))
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  fd.append('source_type', photo.value.source_type)
  if (photo.value.source_note.trim()) fd.append('source_note', photo.value.source_note.trim())
  const ok = await act(async () => (await raw(`/api/v1/admin/catalog/items/${props.item.id}/images`, { method: 'POST', body: fd })).json())
  uploading.value = false
  if (ok) {
    if (fileInput.value) fileInput.value.value = ''
    photo.value = { ...photo.value, source_note: '', rights: false }
  }
}
function makePrimary(id: string) {
  return act(() => call(client.POST('/api/v1/admin/catalog/images/{image_id}/primary', { params: { path: { image_id: id } } })))
}
function removeImage(id: string) {
  return act(() => call(client.DELETE('/api/v1/admin/catalog/images/{image_id}', { params: { path: { image_id: id } } })))
}
</script>
