<template>
  <div class="flex flex-1 flex-col items-center justify-center p-4 md:py-16">
    <section class="flex w-full max-w-md flex-col gap-4 rounded-card border border-line bg-surface p-6">
      <span class="flex size-14 items-center justify-center self-center rounded-full bg-primary-soft"><UIIcon name="home" :size="28" /></span>
      <h1 class="m-0 text-center text-[22px] font-bold">{{ t('noWorkshop.title') }}</h1>
      <p class="m-0 text-center text-muted">{{ t('noWorkshop.text') }}</p>
      <form class="flex flex-col gap-4" novalidate @submit.prevent="create">
        <UIField v-model="name" :label="t('auth.workshop')" :placeholder="t('auth.workshopPlaceholder')" />
        <UISelect v-model="country" :label="t('auth.country')" :options="options" />
        <p v-if="error" role="alert" class="m-0 rounded-control bg-danger-bg p-3 text-danger">{{ error }}</p>
        <UIButton type="submit" size="lg" block :loading="busy" :disabled="!name.trim()">{{ t('noWorkshop.create') }}</UIButton>
      </form>
      <p class="m-0 text-center text-[14px] text-muted">{{ t('noWorkshop.invited') }}</p>
      <RouterLink v-if="session.isAdmin" :to="{ name: 'admin' }" :class="buttonClass('outline', 'md')">
        <UIIcon name="key" :size="18" />{{ t('noWorkshop.toAdmin') }}
      </RouterLink>
    </section>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { useSession } from '@/stores/session'

/** Shown instead of stock pages when the account belongs to no workshop yet
 * (e.g. an admin account, or someone removed from their only workshop). */
const { t, locale } = useI18n()
const session = useSession()
const name = ref('')
const country = ref('UA')
const busy = ref(false)
const error = ref('')

const countries = useQuery({
  queryKey: ['countries'],
  queryFn: () => call(client.GET('/api/v1/reference/countries')),
  staleTime: Infinity,
})
const options = computed(() => {
  const names = new Intl.DisplayNames([locale.value], { type: 'region' })
  return (countries.data.value ?? [])
    .map((c) => ({ value: c.code, label: names.of(c.code) ?? c.name }))
    .sort((a, b) => a.label.localeCompare(b.label, locale.value))
})

async function create() {
  if (!name.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const w = await call(client.POST('/api/v1/workshops', { body: { name: name.value.trim(), country_code: country.value } }))
    await session.load()
    session.selectWorkshop(w.id)
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
