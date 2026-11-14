<template>
  <PageHeader :title="t('admin.brands.title')" :subtitle="t('admin.brands.subtitle')" />
  <div class="grid gap-4 p-3 md:p-0 md:pb-12 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
    <LoadError v-if="isError && !brands" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="!brands?.length" icon="box" :title="t('admin.brands.empty')" :text="t('admin.brands.emptyText')" />
    <section v-else class="rounded-card border border-line bg-surface">
      <div v-for="b in brands" :key="b.id" class="flex items-center gap-3 border-b border-ground px-4 py-3 last:border-0">
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="font-semibold" :class="b.is_active ? '' : 'text-muted line-through'">{{ b.name }}</span>
          <span v-if="b.website" class="truncate text-[13px] text-muted">{{ b.website }}</span>
        </span>
        <UIButton v-if="canEdit" size="sm" variant="ghost" @click="toggle(b)">{{ b.is_active ? t('admin.brands.hide') : t('admin.brands.show') }}</UIButton>
      </div>
    </section>
    <form v-if="canEdit" class="flex flex-col gap-4 self-start rounded-card border border-line bg-surface p-4" @submit.prevent="add">
      <h2 class="m-0 text-[17px] font-bold">{{ t('admin.brands.add') }}</h2>
      <UIField v-model="name" :label="t('more.name')" placeholder="Errebi" />
      <UIField v-model="website" :label="t('admin.brands.website')" :hint="t('move.optional')" />
      <UIButton type="submit" :disabled="!name.trim()">{{ t('admin.brands.add') }}</UIButton>
    </form>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIEmpty, UIField } from '@kv/ui'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useBrands } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const { data: brands, isPending, isError, error, refetch } = useBrands()
const canEdit = computed(() => session.can('catalog.edit'))
const name = ref('')
const website = ref('')

async function add() {
  if (!name.value.trim()) return
  try {
    await call(client.POST('/api/v1/admin/catalog/brands', { body: { name: name.value.trim(), website: website.value.trim() || null } }))
    name.value = website.value = ''
    qc.invalidateQueries({ queryKey: ['admin-brands'] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
async function toggle(b: Schemas['BrandOut']) {
  try {
    await call(client.PATCH('/api/v1/admin/catalog/brands/{brand_id}', { params: { path: { brand_id: b.id } }, body: { is_active: !b.is_active } }))
    qc.invalidateQueries({ queryKey: ['admin-brands'] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
