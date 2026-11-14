<template>
  <form class="flex flex-1 flex-col gap-5" novalidate @submit.prevent="submit">
    <h1 class="m-0 text-[26px] font-bold tracking-tight">{{ t('auth.newPasswordTitle') }}</h1>
    <UIField
      v-model="password"
      :label="t('auth.newPassword')"
      type="password"
      autocomplete="new-password"
      :hint="t('auth.passwordHint')"
      :show-password-label="t('auth.showPassword')"
      :error="fieldError"
    />
    <div v-if="error" role="alert" class="rounded-control bg-danger-bg px-4 py-3 text-danger">{{ error }}</div>
    <UIButton class="mt-auto" type="submit" size="lg" block :loading="busy">{{ t('auth.savePassword') }}</UIButton>
  </form>
</template>

<script setup lang="ts">
import { UIButton, UIField } from '@kv/ui'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const session = useSession()
const password = ref('')
const error = ref('')
const fieldError = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = fieldError.value = ''
  try {
    await call(
      client.POST('/api/v1/auth/reset-password', {
        body: { token: String(route.query.token ?? ''), new_password: password.value },
      }),
    )
    await session.logout()
    toast.show(t('auth.passwordChanged'))
    router.replace({ name: 'login' })
  } catch (e) {
    fieldError.value = fieldErrors(e).new_password ?? ''
    if (!fieldError.value) error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>
