<template>
  <div class="flex min-h-dvh flex-col md:flex-row">
    <aside class="sticky top-0 z-30 flex shrink-0 flex-col gap-3 bg-graphite px-3 pt-3 pb-2 md:h-dvh md:w-56 md:gap-6 md:overflow-y-auto md:py-5 lg:w-64">
      <div class="flex items-center justify-between gap-2 px-1 md:px-2">
        <Logo dark />
        <span class="rounded-md bg-primary px-2 py-0.5 text-xs font-bold text-on-primary">{{ t('admin.badge') }}</span>
      </div>
      <nav :aria-label="t('admin.nav.label')" class="-mx-3 flex gap-1 overflow-x-auto px-3 md:mx-0 md:flex-col md:px-0">
        <RouterLink
          v-for="i in items"
          :key="i.name"
          :to="{ name: i.name }"
          class="flex h-10 shrink-0 items-center gap-2.5 rounded-[10px] px-3 text-[15px] no-underline md:h-11 md:gap-3"
          :class="active(i.match) ? 'bg-primary font-bold text-on-primary' : 'font-medium text-on-graphite hover:bg-white/10'"
          :aria-current="active(i.match) ? 'page' : undefined"
        >
          <UIIcon :name="i.icon" :size="20" />
          <span class="md:flex-1">{{ i.label }}</span>
          <span
            v-if="i.badge"
            class="flex h-[22px] min-w-[22px] items-center justify-center rounded-full px-1.5 text-xs font-bold"
            :class="active(i.match) ? 'bg-ink text-primary' : 'bg-primary text-on-primary'"
          >{{ i.badge }}</span>
        </RouterLink>
        <RouterLink :to="{ name: 'stock' }" class="flex h-10 shrink-0 items-center gap-2 rounded-[10px] px-3 text-[15px] font-semibold text-primary no-underline md:hidden">
          <UIIcon name="back" :size="20" />{{ t('admin.toApp') }}
        </RouterLink>
      </nav>
      <RouterLink
        :to="{ name: 'stock' }"
        class="mt-auto hidden items-center gap-2 rounded-[10px] px-3 py-2 text-[15px] font-semibold text-primary no-underline hover:bg-white/10 md:flex"
      >
        <UIIcon name="back" :size="20" />{{ t('admin.toApp') }}
      </RouterLink>
    </aside>
    <main class="mx-auto flex w-full max-w-6xl min-w-0 flex-1 flex-col md:px-6 lg:px-10">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Logo from '@/components/Logo.vue'
import { call, client } from '@/lib/api'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const route = useRoute()
const session = useSession()
const CATALOG = ['catalog.view', 'catalog.edit', 'catalog.moderate', 'catalog.import']

const pending = useQuery({
  queryKey: ['admin-pending-count'],
  queryFn: () => call(client.GET('/api/v1/admin/catalog/proposals', { params: { query: { limit: 1 } } })),
  enabled: computed(() => session.can(...CATALOG)),
  refetchInterval: 60_000,
})

const items = computed(() =>
  [
    { name: 'admin', icon: 'home', label: t('admin.nav.overview'), show: true, match: ['admin'] },
    { name: 'admin-catalog', icon: 'key', label: t('admin.nav.catalog'), show: session.can(...CATALOG), match: ['admin-catalog', 'admin-item', 'admin-item-new'] },
    { name: 'admin-proposals', icon: 'list', label: t('admin.nav.proposals'), show: session.can(...CATALOG), match: ['admin-proposals'], badge: pending.data.value?.total },
    { name: 'admin-import', icon: 'upload', label: t('admin.nav.import'), show: session.can('catalog.import'), match: ['admin-import'] },
    { name: 'admin-brands', icon: 'box', label: t('admin.nav.brands'), show: session.can(...CATALOG), match: ['admin-brands'] },
    { name: 'admin-history', icon: 'file', label: t('admin.nav.history'), show: session.can(...CATALOG), match: ['admin-history'] },
    { name: 'admin-users', icon: 'users', label: t('admin.nav.users'), show: session.can('users.view'), match: ['admin-users'] },
    { name: 'admin-waitlist', icon: 'list', label: t('admin.nav.waitlist'), show: session.can('users.view'), match: ['admin-waitlist'] },
  ].filter((i) => i.show),
)
const active = (m: string[]) => m.includes(String(route.name))
</script>
