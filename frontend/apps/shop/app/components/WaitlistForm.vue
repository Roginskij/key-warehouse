<template>
  <section id="waitlist" class="flex flex-col gap-4 rounded-card border border-line bg-surface p-5">
    <div class="flex flex-col gap-1">
      <h2 class="m-0 text-[20px] font-bold">{{ t('waitlist.title') }}</h2>
      <p class="m-0 text-muted">{{ t('waitlist.text') }}</p>
    </div>
    <p v-if="done" role="status" class="m-0 rounded-control bg-primary-soft px-4 py-3 font-semibold">{{ t('waitlist.done') }}</p>
    <form v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <UIField v-model="email" class="sm:col-span-2" :label="t('waitlist.email')" type="email" inputmode="email" autocomplete="email" :error="errors.email" />
      <UISelect v-model="role" :label="t('waitlist.role')" :options="roleOptions" />
      <UISelect v-model="country" :label="t('waitlist.country')" :options="countryOptions" />
      <label class="flex items-start gap-3 text-[14px] sm:col-span-2">
        <input v-model="consent" type="checkbox" class="mt-0.5 size-5 shrink-0 accent-ink" />
        <span>{{ t('waitlist.consent') }}</span>
      </label>
      <p v-if="errors.consent" class="m-0 text-[14px] text-danger sm:col-span-2">{{ errors.consent }}</p>
      <UIButton type="submit" size="lg" :loading="busy" class="sm:col-span-2 sm:justify-self-start">{{ t('waitlist.submit') }}</UIButton>
    </form>
  </section>
</template>

<script setup lang="ts">
import { UIButton, UIField, UISelect } from '@kv/ui'

const props = defineProps<{ source?: string }>()
const { t, lang } = useLang()

const COUNTRIES = ['UA', 'PL', 'DE', 'AT', 'CZ', 'SK', 'RO', 'LT', 'LV', 'EE', 'FR', 'BE', 'NL', 'ES', 'PT', 'IT']
const DEFAULT_COUNTRY: Record<string, string> = { uk: 'UA', pl: 'PL', de: 'DE', fr: 'FR', es: 'ES', it: 'IT' }

const email = ref('')
const role = ref<'workshop' | 'car_owner' | 'other'>('workshop')
const country = ref(DEFAULT_COUNTRY[lang.value] ?? '')
const consent = ref(false)
const errors = ref<Record<string, string>>({})
const busy = ref(false)
const done = ref(false)

const roleOptions = computed(() => (['workshop', 'car_owner', 'other'] as const).map((r) => ({ value: r, label: t(`waitlist.roles.${r}`) })))
const countryOptions = computed(() => {
  const names = new Intl.DisplayNames([lang.value], { type: 'region' })
  return [{ value: '', label: '—' }, ...COUNTRIES.map((c) => ({ value: c, label: names.of(c) ?? c })).sort((a, b) => a.label.localeCompare(b.label, lang.value))]
})

async function submit() {
  errors.value = {}
  if (!/^\S+@\S+\.\S+$/.test(email.value.trim())) errors.value.email = t('waitlist.badEmail')
  if (!consent.value) errors.value.consent = t('waitlist.needConsent')
  if (Object.keys(errors.value).length) return
  busy.value = true
  try {
    await apiFetch('/waitlist', {
      method: 'POST',
      body: { email: email.value.trim(), role: role.value, country: country.value || null, locale: lang.value, consent: true, source: props.source ?? null },
    })
    done.value = true
  } catch {
    errors.value.email = t('waitlist.badEmail')
  } finally {
    busy.value = false
  }
}
</script>
