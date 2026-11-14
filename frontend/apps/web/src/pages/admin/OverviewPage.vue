<template>
  <PageHeader :title="t('admin.overview.title')" :subtitle="t('admin.overview.subtitle')" />
  <div class="flex flex-col gap-4 p-3 md:p-0 md:pb-12">
    <LoadError v-if="isError && !m" :error="error" @retry="refetch()" />
    <div v-else-if="isPending" class="h-32 animate-pulse rounded-card bg-surface" />
    <template v-else-if="m">
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div v-for="tile in tiles" :key="tile.label" class="flex flex-col gap-1 rounded-card border border-line bg-surface p-4">
          <span class="text-[14px] text-muted">{{ tile.label }}</span>
          <span class="text-[30px] leading-none font-bold tabular-nums">{{ tile.value }}</span>
          <span class="text-[13px] text-muted">{{ tile.hint }}</span>
        </div>
      </section>
      <p class="m-0 text-[14px] text-muted">{{ t('admin.overview.planNote') }}</p>

      <RouterLink
        v-if="m.pending_proposals"
        :to="{ name: 'admin-proposals' }"
        class="flex items-center gap-3 rounded-card border border-line bg-primary-soft p-4 font-semibold text-ink no-underline"
      >
        <UIIcon name="list" :size="22" />{{ t('admin.overview.reviewQueue', { n: m.pending_proposals }) }}
        <UIIcon name="chevron" :size="20" class="ml-auto" />
      </RouterLink>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section class="overflow-x-auto rounded-card border border-line bg-surface">
          <h2 class="m-0 px-4 pt-4 text-[17px] font-bold">{{ t('admin.overview.byCountry') }}</h2>
          <p v-if="!m.by_country.length" class="m-0 px-4 pt-2 pb-5 text-muted">{{ t('admin.overview.noWorkshops') }}</p>
          <table v-else class="mt-2 w-full min-w-[420px] border-collapse text-[15px]">
            <thead>
              <tr class="text-left text-[13px] text-muted">
                <th class="px-4 py-2 font-semibold">{{ t('auth.country') }}</th>
                <th class="px-2 py-2 text-right font-semibold">{{ t('admin.overview.workshops') }}</th>
                <th class="px-2 py-2 text-right font-semibold">{{ t('admin.overview.moved') }}</th>
                <th class="px-4 py-2 text-right font-semibold">{{ t('admin.overview.active') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in m.by_country" :key="r.country" class="border-t border-ground">
                <td class="px-4 py-2.5 font-semibold">{{ country(r.country) }}</td>
                <td class="px-2 py-2.5 text-right tabular-nums">{{ num(r.workshops) }}</td>
                <td class="px-2 py-2.5 text-right tabular-nums">{{ num(r.moved_stock) }} <span class="text-muted">· {{ pct(r.moved_stock, r.workshops) }}%</span></td>
                <td class="px-4 py-2.5 text-right tabular-nums">{{ num(r.active_7d) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <div class="flex flex-col gap-4">
          <section class="rounded-card border border-line bg-surface p-4">
            <h2 class="m-0 mb-2 text-[17px] font-bold">{{ t('admin.overview.byLanguage') }}</h2>
            <p v-if="!m.by_locale.length" class="m-0 text-muted">—</p>
            <dl class="m-0 grid grid-cols-[1fr_auto] gap-y-1.5 text-[15px]">
              <template v-for="r in m.by_locale" :key="r.locale">
                <dt>{{ lang(r.locale) }}</dt><dd class="m-0 text-right font-semibold tabular-nums">{{ num(r.users) }}</dd>
              </template>
            </dl>
          </section>
          <section class="rounded-card border border-line bg-surface p-4">
            <h2 class="m-0 mb-2 text-[17px] font-bold">{{ t('admin.overview.byWeek') }}</h2>
            <p v-if="!m.registrations_by_week.length" class="m-0 text-muted">{{ t('admin.overview.noRegistrations') }}</p>
            <dl class="m-0 grid grid-cols-[1fr_auto] gap-y-1.5 text-[15px]">
              <template v-for="w in m.registrations_by_week" :key="w.week_start">
                <dt>{{ t('admin.overview.weekOf', { date: weekLabel(w.week_start) }) }}</dt>
                <dd class="m-0 text-right font-semibold tabular-nums">{{ num(w.workshops) }}</dd>
              </template>
            </dl>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { UIIcon } from '@kv/ui'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadError from '@/components/LoadError.vue'
import PageHeader from '@/components/PageHeader.vue'
import { call, client } from '@/lib/api'
import { errorText } from '@/lib/errors'
import { num } from '@/lib/format'
import { LOCALES } from '@/i18n'

const { t, locale } = useI18n()
const { data: m, isPending, isError, error, refetch } = useQuery({
  queryKey: ['admin-metrics'],
  queryFn: () => call(client.GET('/api/v1/admin/metrics')),
})

const pct = (part: number, whole: number) => (whole ? Math.round((part / whole) * 100) : 0)
const country = (code: string) => new Intl.DisplayNames([locale.value], { type: 'region' }).of(code) ?? code
const lang = (code: string) => LOCALES.find((l) => l.code === code)?.name ?? code
const weekLabel = (iso: string) =>
  new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short' }).format(new Date(iso))

const tiles = computed(() => {
  const v = m.value
  if (!v) return []
  return [
    { label: t('admin.overview.workshops'), value: num(v.workshops), hint: t('admin.overview.users', { n: num(v.users) }) },
    { label: t('admin.overview.moved'), value: `${pct(v.moved_stock, v.workshops)}%`, hint: t('admin.overview.movedHint', { n: num(v.moved_stock) }) },
    { label: t('admin.overview.active'), value: `${pct(v.active_7d, v.moved_stock || v.workshops)}%`, hint: t('admin.overview.activeHint', { n: num(v.active_7d) }) },
    { label: t('admin.overview.catalog'), value: num(v.catalog_items), hint: t('admin.overview.pending', { n: num(v.pending_proposals) }) },
    { label: t('admin.overview.waitlist'), value: num(v.waitlist), hint: t('admin.overview.waitlistHint') },
  ]
})
</script>
