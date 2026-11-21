<template>
  <div v-if="fields.length" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <template v-for="f in fields" :key="f.key">
      <UISelect
        v-if="f.type === 'select'"
        :model-value="String(model[f.key] ?? '')"
        :label="label(kind, f.key)"
        :options="[{ value: '', label: '—' }, ...f.options.map((o) => ({ value: o.key, label: value(kind, f.key, o.key) }))]"
        :error="error === f.key ? t('attrs.bad') : undefined"
        @update:model-value="set(f.key, $event || null)"
      />
      <UIField
        v-else-if="f.type === 'number'"
        :model-value="model[f.key] == null ? '' : String(model[f.key])"
        :label="label(kind, f.key)"
        inputmode="numeric"
        :error="error === f.key ? t('attrs.bad') : undefined"
        @update:model-value="set(f.key, String($event ?? '').trim() === '' ? null : Number($event))"
      />
      <label v-else class="flex items-center gap-3 self-end py-2 text-[15px] font-semibold">
        <input type="checkbox" class="size-5 accent-ink" :checked="model[f.key] === true" @change="set(f.key, ($event.target as HTMLInputElement).checked)" />
        {{ label(kind, f.key) }}
      </label>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIField, UISelect } from '@kv/ui'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { type Attributes, useAttributeSpec, useAttributeText } from '@/lib/queries'

const props = defineProps<{ kind: string; error?: string | null }>()
const model = defineModel<Attributes>({ required: true })
const { t } = useI18n()
const { data: spec } = useAttributeSpec()
const { label, value } = useAttributeText()
const fields = computed(() => spec.value?.[props.kind] ?? [])

function set(key: string, v: unknown) {
  const next = { ...model.value }
  if (v === null || v === undefined || (typeof v === 'number' && Number.isNaN(v))) delete next[key]
  else next[key] = v
  model.value = next
}
</script>
