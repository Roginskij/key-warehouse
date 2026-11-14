<template>
  <form class="flex flex-1 flex-col gap-4" novalidate @submit.prevent="submit">
    <div class="flex flex-col gap-1">
      <h1 class="m-0 text-[26px] font-bold tracking-tight">{{ t('auth.registerTitle') }}</h1>
      <p class="m-0 text-muted">{{ t('auth.registerSubtitle') }}</p>
    </div>
    <UIField v-model="form.full_name" :label="t('auth.name')" autocomplete="name" :error="errors.full_name" />
    <UIField v-model="form.email" :label="t('auth.email')" type="email" autocomplete="email" inputmode="email" :error="errors.email" />
    <UIField
      v-model="form.password"
      :label="t('auth.password')"
      type="password"
      autocomplete="new-password"
      :hint="t('auth.passwordHint')"
      :show-password-label="t('auth.showPassword')"
      :error="errors.password"
    />
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UISelect v-model="form.country_code" :label="t('auth.country')" :options="countryOptions" :error="errors.country_code" />
      <UIField v-model="form.workshop_name" :label="t('auth.workshop')" :placeholder="t('auth.workshopPlaceholder')" :error="errors.workshop_name" />
    </div>
    <label class="flex items-start gap-3 pt-1 text-[15px] leading-snug">
      <input v-model="form.accept_terms" type="checkbox" class="mt-0.5 size-6 shrink-0 accent-ink" />
      <span>{{ t('auth.terms') }}</span>
    </label>
    <p v-if="errors.accept_terms" class="m-0 -mt-2 text-sm font-medium text-danger">{{ errors.accept_terms }}</p>
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-[15px] text-danger">{{ error }}</div>
    <div class="mt-auto flex flex-col gap-3 pt-4">
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('auth.registerButton') }}</UIButton>
      <p class="m-0 text-center text-[15px] text-muted">
        {{ t('auth.haveAccount') }}
        <RouterLink :to="{ name: 'login' }" class="font-semibold text-ink">{{ t('auth.loginButton') }}</RouterLink>
      </p>
    </div>
  </form>
</template>

<script setup lang="ts">
import { UIButton, UIField, UISelect } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'

const { t, locale } = useI18n()
const router = useRouter()

const { data: countries } = useQuery({
  queryKey: ['countries'],
  queryFn: () => call(client.GET('/api/v1/reference/countries')),
  staleTime: Infinity,
})

const DEFAULT_COUNTRY: Record<string, string> = { uk: 'UA', pl: 'PL', de: 'DE', fr: 'FR', es: 'ES', it: 'IT', en: 'UA' }
const form = ref({
  full_name: '',
  email: '',
  password: '',
  country_code: DEFAULT_COUNTRY[locale.value] ?? 'UA',
  workshop_name: '',
  accept_terms: false,
})
const errors = ref<Record<string, string>>({})
const error = ref('')
const busy = ref(false)

const countryOptions = computed(() => {
  const names = new Intl.DisplayNames([locale.value], { type: 'region' })
  return (countries.value ?? [])
    .map((c) => ({ value: c.code, label: names.of(c.code) ?? c.name }))
    .sort((a, b) => a.label.localeCompare(b.label, locale.value))
})

async function submit() {
  errors.value = {}
  error.value = ''
  if (!form.value.accept_terms) {
    errors.value.accept_terms = t('auth.termsRequired')
    return
  }
  busy.value = true
  try {
    await call(client.POST('/api/v1/auth/register', { body: { ...form.value, locale: locale.value } }))
    router.push({ name: 'check-email', query: { email: form.value.email } })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
