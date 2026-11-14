<template>
  <PageHeader :title="t('more.title')" :subtitle="session.me?.user.email" />
  <div class="grid gap-3 p-3 md:max-w-3xl md:gap-4 md:p-0 md:pb-12 lg:max-w-none lg:grid-cols-2 lg:gap-5">
    <section class="flex flex-col gap-1 rounded-card border border-line bg-surface p-2 md:hidden">
      <RouterLink v-if="session.seesPurchase" :to="{ name: 'value' }" class="flex min-h-13 items-center gap-3 rounded-[10px] px-3 text-[16px] font-semibold text-ink no-underline hover:bg-ground">
        <UIIcon name="coins" :size="22" />{{ t('nav.value') }}<UIIcon name="chevron" :size="20" class="ml-auto text-faint" />
      </RouterLink>
      <RouterLink :to="{ name: 'import' }" class="flex min-h-13 items-center gap-3 rounded-[10px] px-3 text-[16px] font-semibold text-ink no-underline hover:bg-ground">
        <UIIcon name="upload" :size="22" />{{ t('nav.import') }}<UIIcon name="chevron" :size="20" class="ml-auto text-faint" />
      </RouterLink>
      <RouterLink v-if="session.isAdmin" :to="{ name: 'admin' }" class="flex min-h-13 items-center gap-3 rounded-[10px] px-3 text-[16px] font-semibold text-ink no-underline hover:bg-ground">
        <UIIcon name="key" :size="22" />{{ t('nav.admin') }}<UIIcon name="chevron" :size="20" class="ml-auto text-faint" />
      </RouterLink>
      <RouterLink v-if="session.isOwner" :to="{ name: 'team' }" class="flex min-h-13 items-center gap-3 rounded-[10px] px-3 text-[16px] font-semibold text-ink no-underline hover:bg-ground">
        <UIIcon name="users" :size="22" />{{ t('nav.team') }}<UIIcon name="chevron" :size="20" class="ml-auto text-faint" />
      </RouterLink>
      <RouterLink v-if="session.isOwner" :to="{ name: 'public-profile' }" class="flex min-h-13 items-center gap-3 rounded-[10px] px-3 text-[16px] font-semibold text-ink no-underline hover:bg-ground">
        <UIIcon name="globe" :size="22" />{{ t('nav.publicProfile') }}<UIIcon name="chevron" :size="20" class="ml-auto text-faint" />
      </RouterLink>
    </section>

    <section class="flex flex-col gap-4 rounded-card border border-line bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('more.profile') }}</h2>
      <p class="m-0 text-[16px]"><b>{{ session.me?.user.full_name }}</b><br /><span class="text-muted">{{ session.me?.user.email }}</span></p>
      <UISelect v-model="lang" :label="t('common.language')" :options="langOptions" />
      <UIButton variant="outline" class="self-start" @click="open('password')">{{ t('more.changePassword') }}</UIButton>
      <div class="flex flex-col gap-1 border-t border-ground pt-3">
        <UIButton variant="outline" class="self-start" :loading="exporting" @click="downloadMyData">
          <UIIcon name="download" :size="18" />{{ t('more.myData') }}
        </UIButton>
        <span class="text-[14px] text-muted">{{ t('more.myDataHint') }}</span>
      </div>
    </section>

    <section class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('more.workshop') }}</h2>
      <UISelect v-if="session.workshops.length > 1" v-model="currentWorkshop" :label="t('more.current')" :options="workshopOptions" />
      <p v-if="!session.wid" class="m-0 text-muted">{{ t('noWorkshop.text') }}</p>
      <dl v-else class="m-0 grid grid-cols-2 gap-2 text-[15px]">
        <dt class="text-muted">{{ t('more.name') }}</dt><dd class="m-0 text-right font-semibold">{{ workshop.data.value?.name }}</dd>
        <dt class="text-muted">{{ t('auth.country') }}</dt><dd class="m-0 text-right font-semibold">{{ country }}</dd>
        <dt class="text-muted">{{ t('more.baseCurrency') }}</dt><dd class="m-0 text-right font-semibold">{{ workshop.data.value?.base_currency }}</dd>
        <dt class="text-muted">{{ t('more.role') }}</dt><dd class="m-0 text-right font-semibold">{{ session.workshop ? t(`roles.${session.workshop.role}`) : '' }}</dd>
      </dl>
      <div class="flex flex-wrap gap-2 border-t border-ground pt-3">
        <UIButton v-if="session.isOwner" variant="outline" @click="open('workshop')"><UIIcon name="edit" :size="18" />{{ t('common.edit') }}</UIButton>
        <UIButton variant="ghost" @click="open('newWorkshop')"><UIIcon name="plus" :size="18" :stroke="2.6" />{{ t('more.newWorkshop') }}</UIButton>
      </div>
    </section>

    <section v-if="session.isOwner" class="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
      <h2 class="m-0 text-[17px] font-bold">{{ t('more.rates') }}</h2>
      <p class="m-0 text-[15px] text-muted">{{ t('more.ratesText', { base: workshop.data.value?.base_currency ?? '' }) }}</p>
      <ul v-if="rates.data.value?.length" class="m-0 list-none p-0 text-[16px]">
        <li v-for="r in rates.data.value" :key="r.currency" class="flex justify-between py-1">
          <span>1 {{ r.currency }}</span><b>{{ Number(r.rate) }} {{ workshop.data.value?.base_currency }}</b>
        </li>
      </ul>
      <form class="grid grid-cols-[6rem_minmax(0,1fr)] items-end gap-2 sm:grid-cols-[6rem_minmax(0,1fr)_auto]" @submit.prevent="saveRate">
        <UISelect v-model="rateCur" :label="t('item.form.currency')" :options="rateOptions" />
        <UIField v-model="rateVal" :label="t('more.rate')" inputmode="decimal" placeholder="41.50" />
        <UIButton type="submit" class="col-span-2 h-12 sm:col-span-1">{{ t('common.save') }}</UIButton>
      </form>
    </section>

    <section class="flex flex-col gap-2 rounded-card border border-line bg-surface p-4 md:flex-row md:items-center md:justify-between lg:col-span-2">
      <UIButton variant="outline" @click="logout"><UIIcon name="logout" :size="18" />{{ t('more.logout') }}</UIButton>
      <button type="button" class="self-start text-[15px] font-semibold text-danger underline md:self-auto" @click="open('delete')">{{ t('more.deleteAccount') }}</button>
    </section>
  </div>

  <Sheet :open="sheet === 'password'" :title="t('more.changePassword')" :close-label="t('common.close')" @close="sheet = null">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="changePassword">
      <UIField v-model="pw.current_password" :label="t('more.currentPassword')" type="password" autocomplete="current-password" :show-password-label="t('auth.showPassword')" :error="errors.current_password" />
      <UIField v-model="pw.new_password" :label="t('auth.newPassword')" type="password" autocomplete="new-password" :hint="t('auth.passwordHint')" :show-password-label="t('auth.showPassword')" :error="errors.new_password" />
      <p class="m-0 text-[14px] text-muted">{{ t('more.passwordLogoutHint') }}</p>
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('auth.savePassword') }}</UIButton>
    </form>
  </Sheet>

  <Sheet :open="sheet === 'workshop'" :title="t('more.editWorkshop')" :close-label="t('common.close')" @close="sheet = null">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="saveWorkshop">
      <UIField v-model="wsForm.name" :label="t('auth.workshop')" :error="errors.name" />
      <UISelect v-model="wsForm.country_code" :label="t('auth.country')" :options="countryOptions" />
      <UISelect v-model="wsForm.base_currency" :label="t('more.baseCurrency')" :options="currencyOptions" />
      <p class="m-0 text-[14px] text-muted">{{ t('more.currencyHint') }}</p>
      <UIButton type="submit" size="lg" block :loading="busy">{{ t('common.save') }}</UIButton>
    </form>
  </Sheet>

  <Sheet :open="sheet === 'newWorkshop'" :title="t('more.newWorkshop')" :close-label="t('common.close')" @close="sheet = null">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="createWorkshop">
      <p class="m-0 text-[15px] text-muted">{{ t('more.newWorkshopHint') }}</p>
      <UIField v-model="newWs.name" :label="t('auth.workshop')" :placeholder="t('auth.workshopPlaceholder')" :error="errors.name" />
      <UISelect v-model="newWs.country_code" :label="t('auth.country')" :options="countryOptions" />
      <UIButton type="submit" size="lg" block :loading="busy" :disabled="!newWs.name.trim()">{{ t('more.create') }}</UIButton>
    </form>
  </Sheet>

  <Sheet :open="sheet === 'delete'" :title="t('more.deleteAccount')" :close-label="t('common.close')" @close="sheet = null">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="deleteAccount">
      <p class="m-0 text-[15px]">{{ t('more.deleteWarning') }}</p>
      <UIField v-model="delPassword" :label="t('auth.password')" type="password" autocomplete="current-password" :show-password-label="t('auth.showPassword')" :error="errors.password" />
      <UIButton type="submit" variant="danger" size="lg" block :loading="busy" :disabled="!delPassword">{{ t('more.deleteForever') }}</UIButton>
    </form>
  </Sheet>
</template>

<script setup lang="ts">
import { ApiError } from '@kv/api'
import { UIButton, UIField, UIIcon, UISelect } from '@kv/ui'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import Sheet from '@/components/Sheet.vue'
import { LOCALES } from '@/i18n'
import { call, client, raw } from '@/lib/api'
import { errorText, fieldErrors } from '@/lib/errors'
import { useCurrencies } from '@/lib/queries'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const { t, locale } = useI18n()
const router = useRouter()
const session = useSession()
const toast = useToast()
const qc = useQueryClient()
const { data: currencies } = useCurrencies()

const workshop = useQuery({
  queryKey: computed(() => ['workshop', session.wid]),
  queryFn: () => call(client.GET('/api/v1/workshops/{workshop_id}', { params: { path: { workshop_id: session.wid } } })),
  enabled: computed(() => !!session.wid),
})
const rates = useQuery({
  queryKey: computed(() => ['rates', session.wid]),
  queryFn: () => call(client.GET('/api/v1/workshops/{workshop_id}/inventory/rates', { params: { path: { workshop_id: session.wid } } })),
  enabled: computed(() => !!session.wid),
})

const lang = computed({
  get: () => locale.value,
  set: (v: string) => session.updateMe({ locale: v }).catch((e) => toast.error(errorText(e))),
})
const langOptions = LOCALES.map((l) => ({ value: l.code, label: l.name }))
const country = computed(() => {
  const c = workshop.data.value?.country_code
  return c ? new Intl.DisplayNames([locale.value], { type: 'region' }).of(c) : ''
})

const rateCur = ref('USD')
const rateVal = ref('')
const rateOptions = computed(() =>
  (currencies.value ?? []).filter((c) => c.code !== workshop.data.value?.base_currency).map((c) => ({ value: c.code, label: c.code })),
)
async function saveRate() {
  if (!rateVal.value.trim()) return
  try {
    await call(
      client.PUT('/api/v1/workshops/{workshop_id}/inventory/rates/{currency}', {
        params: { path: { workshop_id: session.wid, currency: rateCur.value } },
        body: { rate: rateVal.value.replace(',', '.') },
      }),
    )
    rateVal.value = ''
    qc.invalidateQueries({ queryKey: ['rates', session.wid] })
    qc.invalidateQueries({ queryKey: ['items', session.wid] })
    toast.show(t('more.rateSaved'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

const exporting = ref(false)
async function downloadMyData() {
  exporting.value = true
  try {
    const res = await raw('/api/v1/users/me/export')
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement('a')
    a.href = url
    a.download = `keyverhaus-my-data-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(errorText(e))
  } finally {
    exporting.value = false
  }
}

async function logout() {
  await session.logout()
  qc.clear()
  router.replace({ name: 'login' })
}

const countriesQ = useQuery({
  queryKey: ['countries'],
  queryFn: () => call(client.GET('/api/v1/reference/countries')),
  staleTime: Infinity,
})
const countryOptions = computed(() => {
  const names = new Intl.DisplayNames([locale.value], { type: 'region' })
  return (countriesQ.data.value ?? [])
    .map((c) => ({ value: c.code, label: names.of(c.code) ?? c.name }))
    .sort((a, b) => a.label.localeCompare(b.label, locale.value))
})
const currencyOptions = computed(() => (currencies.value ?? []).map((c) => ({ value: c.code, label: c.code })))
const workshopOptions = computed(() => session.workshops.map((w) => ({ value: w.workshop_id, label: w.workshop_name })))
const currentWorkshop = computed({
  get: () => session.wid,
  set: (id: string) => {
    session.selectWorkshop(id)
    toast.show(t('more.switched', { name: session.workshop?.workshop_name ?? '' }))
  },
})

// --- open sheet: which form is shown
const sheet = ref<null | 'password' | 'workshop' | 'newWorkshop' | 'delete'>(null)
const busy = ref(false)
const errors = ref<Record<string, string>>({})
function open(kind: NonNullable<typeof sheet.value>) {
  errors.value = {}
  if (kind === 'workshop' && workshop.data.value) {
    wsForm.value = {
      name: workshop.data.value.name,
      country_code: workshop.data.value.country_code,
      base_currency: workshop.data.value.base_currency,
    }
  }
  if (kind === 'newWorkshop') newWs.value = { name: '', country_code: workshop.data.value?.country_code ?? 'UA' }
  if (kind === 'password') pw.value = { current_password: '', new_password: '' }
  if (kind === 'delete') delPassword.value = ''
  sheet.value = kind
}

const pw = ref({ current_password: '', new_password: '' })
async function changePassword() {
  busy.value = true
  errors.value = {}
  try {
    await call(client.POST('/api/v1/auth/change-password', { body: pw.value }))
    sheet.value = null
    await session.logout()
    qc.clear()
    toast.show(t('auth.passwordChanged'))
    router.replace({ name: 'login' })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (e instanceof ApiError && e.code === 'auth.wrong_password') errors.value.current_password = errorText(e)
    else if (!Object.keys(errors.value).length) toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}

const wsForm = ref({ name: '', country_code: '', base_currency: '' })
async function saveWorkshop() {
  busy.value = true
  errors.value = {}
  try {
    await call(client.PATCH('/api/v1/workshops/{workshop_id}', { params: { path: { workshop_id: session.wid } }, body: wsForm.value }))
    sheet.value = null
    await session.load()
    qc.invalidateQueries({ queryKey: ['workshop', session.wid] })
    qc.invalidateQueries({ queryKey: ['items', session.wid] })
    qc.invalidateQueries({ queryKey: ['rates', session.wid] })
    toast.show(t('more.workshopSaved'))
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}

const newWs = ref({ name: '', country_code: 'UA' })
async function createWorkshop() {
  busy.value = true
  errors.value = {}
  try {
    const w = await call(client.POST('/api/v1/workshops', { body: newWs.value }))
    sheet.value = null
    await session.load()
    session.selectWorkshop(w.id)
    toast.show(t('more.workshopCreated', { name: w.name }))
    router.push({ name: 'stock' })
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}

const delPassword = ref('')
async function deleteAccount() {
  busy.value = true
  errors.value = {}
  try {
    await call(client.DELETE('/api/v1/users/me', { body: { password: delPassword.value } }))
    sheet.value = null
    await session.logout()
    qc.clear()
    toast.show(t('more.deleted'))
    router.replace({ name: 'login' })
  } catch (e) {
    if (e instanceof ApiError && e.code === 'auth.wrong_password') errors.value.password = errorText(e)
    else toast.error(errorText(e))
  } finally {
    busy.value = false
  }
}
</script>
