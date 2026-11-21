<template>
  <dl v-if="rows.length" class="m-0 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[15px]">
    <template v-for="r in rows" :key="r.key">
      <dt class="text-muted">{{ r.label }}</dt>
      <dd class="m-0 font-semibold">{{ r.value }}</dd>
    </template>
  </dl>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type Attributes, useAttributeSpec, useAttributeText } from '@/lib/queries'

const props = defineProps<{ kind: string; values: Attributes | null | undefined }>()
const { data: spec } = useAttributeSpec()
const { label, value } = useAttributeText()
// In the order of the kind's list; unknown keys are not shown.
const rows = computed(() =>
  (spec.value?.[props.kind] ?? [])
    .filter((f) => props.values?.[f.key] !== undefined && props.values?.[f.key] !== null)
    .map((f) => ({ key: f.key, label: label(props.kind, f.key), value: value(props.kind, f.key, props.values![f.key]) })),
)
</script>
