<template>
  <div class="flex flex-1 flex-col gap-5">
    <template v-if="info">
      <div class="flex flex-col gap-1">
        <h1 class="m-0 text-[24px] font-bold">{{ t('staffInvite.title') }}</h1>
        <p class="m-0 text-muted">{{ t('staffInvite.subtitle', { email: info.email }) }}</p>
      </div>
      <ul class="m-0 flex flex-col gap-1 rounded-card bg-ground p-3 pl-3 text-[15px]">
        <li v-for="p in info.permissions" :key="p" class="flex list-none items-center gap-2">
          <UIIcon name="check" :size="16" />{{ te(`admin.perms.${key(p)}`) ? t(`admin.perms.${key(p)}`) : p }}
        </li>
      </ul>
      <p class="m-0 text-[14px] text-muted">{{ t('staffInvite.noWorkshop') }}</p>

      <form class="flex flex-col gap-4" novalidate @submit.prevent="accept">
        <UIField v-model="form.full_name" :label="t('auth.name')" autocomplete="name" :error="errors.full_name" />
        <UIField
          v-model="form.password"
          :label="t('auth.password')"
          type="password"
          autocomplete="new-password"
          :hint="t('auth.passwordHint')"
          :show-password-label="t('auth.showPassword')"
          :error="errors.password"
        />
        <label class="flex items-start gap-3 text-[15px]">
          <input v-model="form.accept_terms" type="checkbox" class="mt-0.5 size-6 shrink-0 accent-ink" />
          <span>{{ t('auth.terms') }}</span>
        </label>
        <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
        <UIButton type="submit" size="lg" block :loading="busy">{{ t('staffInvite.create') }}</UIButton>
      </form>
    </template>
    <div v-else-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIField, UIIcon } from '@kv/ui'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { useSession } from '@/stores/session'

const { t, te, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const token = String(route.query.token ?? '')
const key = (p: string) => p.replace('.', '_')

const info = ref<Schemas['StaffPreviewOut'] | null>(null)
const error = ref('')
const errors = ref<Record<string, string>>({})
const busy = ref(false)
const form = ref({ full_name: '', password: '', accept_terms: false })

onMounted(async () => {
  try {
    info.value = await call(client.POST('/api/v1/staff-invitations/preview', { body: { token } }))
  } catch (e) {
    error.value = errorText(e)
  }
})

async function accept() {
  error.value = ''
  errors.value = {}
  if (!form.value.accept_terms) {
    error.value = t('auth.termsRequired')
    return
  }
  busy.value = true
  try {
    const tokens = await call(client.POST('/api/v1/staff-invitations/accept', { body: { token, ...form.value, locale: locale.value } }))
    await session.signInWith(tokens)
    router.replace({ name: 'admin' })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
