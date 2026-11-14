<template>
  <div class="flex flex-col gap-2">
    <span class="text-[15px] font-semibold">{{ t('admin.item.codes') }}</span>
    <div v-for="(r, i) in rows" :key="i" class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto] gap-2">
      <select v-model="r.brand" :aria-label="t('item.form.brand')" class="h-12 rounded-control border-2 border-line-strong bg-surface px-2 text-[16px]">
        <option value="" disabled>{{ t('item.form.brand') }}</option>
        <option v-for="b in brands?.filter((x) => x.is_active)" :key="b.id" :value="b.name">{{ b.name }}</option>
      </select>
      <input v-model="r.code" :aria-label="t('item.form.code')" :placeholder="t('item.form.code')" class="h-12 min-w-0 rounded-control border-2 border-line-strong bg-surface px-3 text-[16px] outline-none focus:border-ink" />
      <button type="button" class="flex size-12 items-center justify-center rounded-control text-muted hover:bg-black/5" :aria-label="t('common.delete')" @click="rows.splice(i, 1)">
        <UIIcon name="close" :size="20" />
      </button>
    </div>
    <UIButton size="sm" variant="outline" class="self-start" @click="rows.push({ brand: '', code: '' })">
      <UIIcon name="plus" :size="16" :stroke="2.6" />{{ t('admin.item.addCode') }}
    </UIButton>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIIcon } from '@kv/ui'
import { useI18n } from 'vue-i18n'
import { useBrands } from '@/lib/admin'

/** Editable list of (brand, code) pairs. */
const rows = defineModel<{ brand: string; code: string }[]>({ required: true })
const { t } = useI18n()
const { data: brands } = useBrands()
</script>
