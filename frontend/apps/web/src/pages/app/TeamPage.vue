<template>
  <PageHeader :title="t('team.title')" :back="{ name: 'more' }" :back-label="t('common.back')" />
  <div class="grid gap-3 p-3 lg:grid-cols-2 md:gap-5 md:p-0 md:pb-12">
    <UIEmpty v-if="!session.isOwner" icon="users" :title="t('team.ownerOnly')" />
    <template v-else>
      <LoadError v-if="members.isError.value && !members.data.value" :error="members.error.value" @retry="members.refetch()" />
      <section v-else class="flex flex-col gap-1 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 mb-2 text-[17px] font-bold">{{ t('team.members') }}</h2>
        <div v-for="m in members.data.value" :key="m.membership_id" class="flex flex-col gap-2 border-b border-ground py-3 last:border-0">
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 flex-col">
              <span class="font-semibold">{{ m.full_name }}<span v-if="m.user_id === session.me?.user.id" class="text-muted"> · {{ t('team.you') }}</span></span>
              <span class="truncate text-[14px] text-muted">{{ m.email }} · {{ t(`roles.${m.role}`) }}</span>
            </div>
            <button
              v-if="m.user_id !== session.me?.user.id"
              type="button"
              class="flex size-10 shrink-0 items-center justify-center rounded-full text-danger hover:bg-danger-bg"
              :aria-label="t('team.remove', { name: m.full_name })"
              @click="removeMember(m.membership_id)"
            ><UIIcon name="trash" :size="18" /></button>
          </div>
          <label v-if="m.role === 'master'" class="flex items-center gap-3 text-[15px]">
            <input type="checkbox" class="size-5 accent-ink" :checked="m.can_see_purchase_prices" @change="togglePrices(m.membership_id, ($event.target as HTMLInputElement).checked)" />
            {{ t('team.seesPrices') }}
          </label>
        </div>
      </section>

      <section class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4">
        <h2 class="m-0 text-[17px] font-bold">{{ t('team.invite') }}</h2>
        <form class="flex flex-col gap-4" novalidate @submit.prevent="invite">
          <UIField v-model="form.email" :label="t('auth.email')" type="email" inputmode="email" autocomplete="off" :error="errors.email" />
          <UISelect v-model="form.role" :label="t('team.role')" :options="roleOptions" />
          <label v-if="form.role === 'master'" class="flex items-center gap-3 text-[15px]">
            <input v-model="form.can_see_purchase_prices" type="checkbox" class="size-5 accent-ink" />{{ t('team.seesPrices') }}
          </label>
          <UIButton type="submit" size="lg" block :loading="busy">{{ t('team.send') }}</UIButton>
        </form>
        <div v-if="pending.length" class="flex flex-col gap-2 pt-2">
          <h3 class="m-0 text-[15px] font-bold">{{ t('team.pending') }}</h3>
          <div v-for="i in pending" :key="i.id" class="flex items-center justify-between gap-2 text-[15px]">
            <span class="min-w-0 truncate">{{ i.email }} <span class="text-muted">· {{ dateTime(i.created_at) }}</span></span>
            <UIButton size="sm" variant="ghost" @click="revoke(i.id)">{{ t('team.revoke') }}</UIButton>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIButton, UIEmpty, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { dateTime } from '@/lib/format'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const path = computed(() => ({ workshop_id: session.wid }))

const members = useQuery({
  queryKey: computed(() => ['members', session.wid]),
  queryFn: () => call(client.GET('/api/v1/workshops/{workshop_id}/members', { params: { path: path.value } })),
  enabled: computed(() => session.isOwner),
})
const invites = useQuery({
  queryKey: computed(() => ['invites', session.wid]),
  queryFn: () => call(client.GET('/api/v1/workshops/{workshop_id}/invitations', { params: { path: path.value } })),
  enabled: computed(() => session.isOwner),
})
const pending = computed(() => (invites.data.value ?? []).filter((i) => !i.accepted_at && !i.revoked_at))

const form = ref({ email: '', role: 'master' as 'master' | 'owner', can_see_purchase_prices: false })
const errors = ref<Record<string, string>>({})
const busy = ref(false)
const roleOptions = computed(() => [
  { value: 'master', label: t('roles.master') },
  { value: 'owner', label: t('roles.owner') },
])

async function invite() {
  errors.value = {}
  busy.value = true
  try {
    await call(client.POST('/api/v1/workshops/{workshop_id}/invitations', { params: { path: path.value }, body: form.value }))
    toast.show(t('team.sent', { email: form.value.email }))
    form.value.email = ''
    qc.invalidateQueries({ queryKey: ['invites', session.wid] })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}

async function togglePrices(membershipId: string, value: boolean) {
  try {
    await call(client.PATCH('/api/v1/workshops/{workshop_id}/members/{membership_id}', {
      params: { path: { ...path.value, membership_id: membershipId } },
      body: { can_see_purchase_prices: value },
    }))
    qc.invalidateQueries({ queryKey: ['members', session.wid] })
  } catch (e) {
    toast.error(errorText(e))
  }
}

async function removeMember(membershipId: string) {
  try {
    await call(client.DELETE('/api/v1/workshops/{workshop_id}/members/{membership_id}', {
      params: { path: { ...path.value, membership_id: membershipId } },
    }))
    qc.invalidateQueries({ queryKey: ['members', session.wid] })
  } catch (e) {
    toast.error(errorText(e))
  }
}

async function revoke(id: string) {
  try {
    await call(client.DELETE('/api/v1/workshops/{workshop_id}/invitations/{invitation_id}', {
      params: { path: { ...path.value, invitation_id: id } },
    }))
    qc.invalidateQueries({ queryKey: ['invites', session.wid] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
