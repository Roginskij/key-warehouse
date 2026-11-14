<template>
  <div class="flex min-h-dvh">
    <aside class="sticky top-0 hidden print:!hidden h-dvh w-56 shrink-0 flex-col gap-6 overflow-y-auto bg-graphite px-3 py-5 md:flex lg:w-64">
      <div class="px-2"><Logo dark /></div>
      <label v-if="session.workshops.length > 1" class="px-1">
        <span class="sr-only">{{ t('common.workshop') }}</span>
        <select
          :value="session.wid"
          class="h-11 w-full rounded-[10px] border border-graphite-2 bg-graphite-2 px-2 text-[15px] font-semibold text-on-graphite"
          @change="session.selectWorkshop(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="w in session.workshops" :key="w.workshop_id" :value="w.workshop_id">{{ w.workshop_name }}</option>
        </select>
      </label>
      <p v-else class="m-0 px-3 text-[15px] font-semibold text-on-graphite-muted">{{ session.workshop?.workshop_name }}</p>
      <nav :aria-label="t('nav.main')" class="flex flex-col gap-1">
        <RouterLink
          v-for="item in side"
          :key="item.name"
          :to="{ name: item.name }"
          class="flex h-11 items-center gap-3 rounded-[10px] px-3 text-[15px] no-underline"
          :class="active(item.match) ? 'bg-primary font-bold text-on-primary' : 'font-medium text-on-graphite hover:bg-white/10'"
          :aria-current="active(item.match) ? 'page' : undefined"
        >
          <UIIcon :name="item.icon" :size="20" />
          <span class="flex-1">{{ item.label }}</span>
          <span
            v-if="item.badge"
            class="flex h-[22px] min-w-[22px] items-center justify-center rounded-full px-1.5 text-xs font-bold"
            :class="active(item.match) ? 'bg-ink text-primary' : 'bg-primary text-on-primary'"
          >{{ item.badge }}</span>
        </RouterLink>
      </nav>
      <div class="mt-auto flex flex-col px-3">
        <span class="text-[15px] font-semibold text-on-graphite">{{ session.me?.user.full_name }}</span>
        <span class="text-[13px] text-on-graphite-muted">{{ session.workshop ? t(`roles.${session.workshop.role}`) : '' }}</span>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col pb-[64px] md:pb-0 print:pb-0">
      <main class="mx-auto flex w-full max-w-6xl flex-1 flex-col md:px-6 lg:px-10 print:max-w-none print:px-0">
        <NoWorkshop v-if="!session.workshops.length && route.name !== 'more'" />
        <RouterView v-else />
      </main>
    </div>

    <nav
      :aria-label="t('nav.main')"
      class="safe-bottom fixed inset-x-0 bottom-0 z-40 grid print:hidden h-16 grid-cols-4 border-t border-graphite-2 bg-graphite md:hidden"
    >
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        class="relative flex flex-col items-center justify-center gap-0.5 border-t-[3px] text-[13px] no-underline"
        :class="active(tab.match) ? 'border-primary font-bold text-primary' : 'border-transparent font-medium text-on-graphite-muted'"
        :aria-current="active(tab.match) ? 'page' : undefined"
      >
        <UIIcon :name="tab.icon" :size="24" />
        <span>{{ tab.label }}</span>
        <span
          v-if="tab.badge"
          class="absolute top-1 left-[54%] flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-xs font-bold text-on-primary"
        >{{ tab.badge }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Logo from '@/components/Logo.vue'
import NoWorkshop from '@/components/NoWorkshop.vue'
import { useReorder } from '@/lib/queries'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const route = useRoute()
const session = useSession()
const { data: reorder } = useReorder()
const lowCount = computed(() => reorder.value?.total ?? 0)

const tabs = computed(() => [
  { name: 'stock', icon: 'box', label: t('nav.stock'), match: ['stock', 'item', 'item-new', 'item-edit'] },
  { name: 'reorder', icon: 'list', label: t('nav.reorder'), match: ['reorder'], badge: lowCount.value },
  { name: 'locations', icon: 'pin', label: t('nav.locations'), match: ['locations'] },
  { name: 'more', icon: 'more', label: t('nav.more'), match: ['more', 'import', 'team', 'value', 'public-profile'] },
])
const side = computed(() => [
  tabs.value[0],
  tabs.value[1],
  tabs.value[2],
  ...(session.seesPurchase ? [{ name: 'value', icon: 'coins', label: t('nav.value'), match: ['value'] }] : []),
  { name: 'import', icon: 'upload', label: t('nav.import'), match: ['import'] },
  ...(session.isOwner ? [{ name: 'team', icon: 'users', label: t('nav.team'), match: ['team'] }] : []),
  ...(session.isOwner ? [{ name: 'public-profile', icon: 'globe', label: t('nav.publicProfile'), match: ['public-profile'] }] : []),
  { name: 'more', icon: 'settings', label: t('nav.settings'), match: ['more'] },
  ...(session.isAdmin ? [{ name: 'admin', icon: 'key', label: t('nav.admin'), match: [] as string[] }] : []),
])
const active = (match: string[]) => match.includes(String(route.name))
</script>
