<template>
  <PageHeader :title="t('admin.users.title')" :subtitle="users.data.value ? t('admin.users.total', { n: users.data.value.total }) : undefined">
    <div class="flex flex-wrap items-center gap-3">
      <label class="flex h-12 flex-1 items-center gap-2.5 rounded-control border-2 border-graphite-2 bg-graphite-2 px-3 text-on-graphite-muted md:max-w-md md:border-line-strong md:bg-surface md:text-muted">
        <UIIcon name="search" :size="22" />
        <input v-model="search" type="search" :placeholder="t('admin.users.search')" :aria-label="t('admin.users.search')" class="min-w-0 flex-1 bg-transparent text-[16px] text-on-graphite outline-none md:text-ink" />
      </label>
      <select v-model="status" :aria-label="t('admin.catalog.status')" class="h-12 rounded-control border-2 border-graphite-2 bg-graphite-2 px-2 text-on-graphite md:border-line-strong md:bg-surface md:text-ink">
        <option value="">{{ t('admin.users.all') }}</option>
        <option v-for="st in ['active', 'blocked', 'deleted']" :key="st" :value="st">{{ t(`admin.users.status.${st}`) }}</option>
      </select>
      <label class="flex items-center gap-2 text-[15px] font-semibold">
        <input v-model="adminsOnly" type="checkbox" class="size-5 accent-primary" />{{ t('admin.users.adminsOnly') }}
      </label>
    </div>
  </PageHeader>

  <div class="flex flex-col gap-2 p-3 md:p-0 md:pb-12">
    <!-- Staff: invited here, get admin rights and no workshop -->
    <section v-if="session.isSuperadmin" class="mb-2 flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="flex flex-col">
          <b class="text-[16px]">{{ t('admin.staff.title') }}</b>
          <span class="text-[14px] text-muted">{{ t('admin.staff.hint') }}</span>
        </span>
        <UIButton @click="inviteOpen = true"><UIIcon name="plus" :size="18" />{{ t('admin.staff.invite') }}</UIButton>
      </div>
      <div v-for="i in staffInvites.data.value" :key="i.id" class="flex items-center justify-between gap-2 border-t border-ground pt-2 text-[15px]">
        <span class="min-w-0 truncate">{{ i.email }} <span class="text-muted">· {{ t('admin.staff.pending') }} · {{ dateTime(i.created_at) }}</span></span>
        <UIButton size="sm" variant="ghost" @click="revokeStaff(i.id)">{{ t('team.revoke') }}</UIButton>
      </div>
    </section>

    <LoadError v-if="users.isError.value && !users.data.value" :error="users.error.value" @retry="users.refetch()" />
    <div v-else-if="users.isPending.value" class="h-40 animate-pulse rounded-card bg-surface" />
    <UIEmpty v-else-if="users.data.value && !users.data.value.items.length" icon="users" :title="t('admin.users.none')" />
    <article v-for="u in users.data.value?.items" :key="u.id" class="flex flex-col gap-3 rounded-[14px] border border-line bg-surface p-4 md:flex-row md:items-center">
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <span class="font-semibold">{{ u.full_name }}
          <span v-if="u.deleted_at" class="ml-1 rounded-md bg-danger-bg px-1.5 py-px text-xs font-bold text-danger">{{ t('admin.users.deletedOn', { date: dateTime(u.deleted_at) }) }}</span>
          <span v-else-if="!u.is_active" class="ml-1 rounded-md bg-danger-bg px-1.5 py-px text-xs font-bold text-danger">{{ t('admin.users.isBlocked') }}</span>
          <span v-if="u.is_superadmin" class="ml-1 rounded-md bg-primary px-1.5 py-px text-xs font-bold">{{ t('admin.users.superadmin') }}</span>
        </span>
        <span class="truncate text-[14px] text-muted">{{ u.email }} · {{ dateTime(u.created_at) }}<template v-if="!u.email_verified"> · {{ t('admin.users.notVerified') }}</template></span>
        <span v-if="u.permissions.length" class="text-[13px] text-muted">{{ u.permissions.map((p) => t(`admin.perms.${p.replace('.', '_')}`)).join(', ') }}</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <UIButton v-if="session.isSuperadmin && !u.is_superadmin" size="sm" variant="outline" @click="openRights(u)">{{ t('admin.users.rights') }}</UIButton>
        <template v-if="u.deleted_at">
          <UIButton v-if="session.can('users.manage')" size="sm" variant="outline" @click="restore(u)">{{ t('admin.users.restore') }}</UIButton>
          <UIButton v-if="session.isSuperadmin" size="sm" variant="danger" @click="purging = u">{{ t('admin.users.purge') }}</UIButton>
        </template>
        <template v-else-if="session.can('users.manage') && !u.is_superadmin && u.id !== session.me?.user.id">
          <UIButton v-if="u.is_active" size="sm" variant="danger" @click="setActive(u, false)">{{ t('admin.users.block') }}</UIButton>
          <UIButton v-else size="sm" variant="outline" @click="setActive(u, true)">{{ t('admin.users.unblock') }}</UIButton>
        </template>
      </div>
    </article>
  </div>

  <Sheet :open="inviteOpen" :title="t('admin.staff.invite')" :close-label="t('common.close')" @close="inviteOpen = false">
    <form class="flex flex-col gap-3" novalidate @submit.prevent="inviteStaff">
      <UIField v-model="staffEmail" :label="t('auth.email')" type="email" inputmode="email" autocomplete="off" />
      <p class="m-0 text-[14px] text-muted">{{ t('admin.staff.emailHint') }}</p>
      <label v-for="p in PERMS" :key="p" class="flex items-start gap-3 rounded-control border border-line p-3">
        <input v-model="staffPerms" type="checkbox" :value="p" class="mt-0.5 size-5 shrink-0 accent-ink" />
        <span class="flex flex-col">
          <span class="font-semibold">{{ t(`admin.perms.${p.replace('.', '_')}`) }}</span>
          <span class="text-[14px] text-muted">{{ t(`admin.permsHint.${p.replace('.', '_')}`) }}</span>
        </span>
      </label>
      <UIButton type="submit" size="lg" block :disabled="!staffEmail.trim() || !staffPerms.length">{{ t('admin.staff.send') }}</UIButton>
    </form>
  </Sheet>

  <Sheet :open="!!purging" :title="t('admin.users.purge')" :close-label="t('common.close')" @close="purging = null">
    <p class="m-0">{{ t('admin.users.purgeWarning', { name: purging?.full_name ?? '', email: purging?.email ?? '' }) }}</p>
    <UIButton variant="danger" size="lg" block @click="purge">{{ t('admin.users.purgeButton') }}</UIButton>
  </Sheet>

  <Sheet :open="!!editing" :title="t('admin.users.rightsFor', { name: editing?.full_name ?? '' })" :close-label="t('common.close')" @close="editing = null">
    <form class="flex flex-col gap-3" @submit.prevent="saveRights">
      <label v-for="p in PERMS" :key="p" class="flex items-start gap-3 rounded-control border border-line p-3">
        <input v-model="picked" type="checkbox" :value="p" class="mt-0.5 size-5 shrink-0 accent-ink" />
        <span class="flex flex-col">
          <span class="font-semibold">{{ t(`admin.perms.${p.replace('.', '_')}`) }}</span>
          <span class="text-[14px] text-muted">{{ t(`admin.permsHint.${p.replace('.', '_')}`) }}</span>
        </span>
      </label>
      <UIButton type="submit" size="lg" block>{{ t('common.save') }}</UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import type { Schemas } from '@kv/api'
import { UIButton, UIEmpty, UIField, UIIcon } from '@kv/ui'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import Sheet from '@/components/Sheet.vue'
import { PERMS } from '@/lib/admin'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { dateTime } from '@/lib/format'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

type U = Schemas['UserOut']
const { t } = useI18n()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()

const search = ref('')
const q = ref('')
let timer: ReturnType<typeof setTimeout>
watch(search, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => (q.value = v.trim()), 250)
})
const adminsOnly = ref(false)
const status = ref<'' | 'active' | 'blocked' | 'deleted'>('')

const users = useQuery({
  queryKey: computed(() => ['admin-users', q.value, adminsOnly.value, status.value]),
  queryFn: () =>
    call(client.GET('/api/v1/admin/users', { params: { query: { q: q.value || undefined, admins_only: adminsOnly.value, status: status.value || undefined, limit: 100 } } })),
  placeholderData: keepPreviousData,
})

async function setActive(u: U, active: boolean) {
  try {
    await call(client.PATCH('/api/v1/admin/users/{user_id}', { params: { path: { user_id: u.id } }, body: { is_active: active } }))
    qc.invalidateQueries({ queryKey: ['admin-users'] })
    toast.show(active ? t('admin.users.unblocked') : t('admin.users.blocked'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

const editing = ref<U | null>(null)
const picked = ref<string[]>([])
function openRights(u: U) {
  editing.value = u
  picked.value = [...u.permissions]
}
async function restore(u: U) {
  try {
    await call(client.POST('/api/v1/admin/users/{user_id}/restore', { params: { path: { user_id: u.id } } }))
    qc.invalidateQueries({ queryKey: ['admin-users'] })
    toast.show(t('admin.users.restored'))
  } catch (e) {
    toast.error(errorText(e))
  }
}
const purging = ref<U | null>(null)
async function purge() {
  const u = purging.value
  if (!u) return
  purging.value = null
  try {
    await call(client.DELETE('/api/v1/admin/users/{user_id}', { params: { path: { user_id: u.id } } }))
    qc.invalidateQueries({ queryKey: ['admin-users'] })
    toast.show(t('admin.users.purged'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

async function saveRights() {
  if (!editing.value) return
  try {
    await call(
      client.PUT('/api/v1/admin/users/{user_id}/permissions', {
        params: { path: { user_id: editing.value.id } },
        body: { permissions: picked.value as Schemas['AdminPerm'][] },
      }),
    )
    editing.value = null
    qc.invalidateQueries({ queryKey: ['admin-users'] })
    toast.show(t('admin.users.rightsSaved'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

// --- staff invitations (superadmin)
const staffInvites = useQuery({
  queryKey: ['staff-invites'],
  queryFn: () => call(client.GET('/api/v1/admin/staff-invitations')),
  enabled: computed(() => session.isSuperadmin),
})
const inviteOpen = ref(false)
const staffEmail = ref('')
const staffPerms = ref<string[]>(['catalog.view', 'catalog.edit', 'catalog.moderate'])
async function inviteStaff() {
  try {
    await call(
      client.POST('/api/v1/admin/staff-invitations', {
        body: { email: staffEmail.value.trim(), permissions: staffPerms.value as Schemas['AdminPerm'][] },
      }),
    )
    toast.show(t('team.sent', { email: staffEmail.value.trim() }))
    inviteOpen.value = false
    staffEmail.value = ''
    qc.invalidateQueries({ queryKey: ['staff-invites'] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
async function revokeStaff(id: string) {
  try {
    await call(client.DELETE('/api/v1/admin/staff-invitations/{invitation_id}', { params: { path: { invitation_id: id } } }))
    qc.invalidateQueries({ queryKey: ['staff-invites'] })
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
