<template>
  <footer class="mt-8 border-t border-line bg-surface">
    <div class="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6 text-[14px] text-muted">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span class="font-semibold text-ink">{{ t('site.language') }}:</span>
        <NuxtLink
          v-for="l in LANGS"
          :key="l"
          :to="switchTo(l)"
          :hreflang="l"
          class="no-underline"
          :class="l === lang ? 'font-bold text-ink' : 'text-muted hover:text-ink'"
        >{{ names[l] }}</NuxtLink>
      </div>
      <p class="m-0 max-w-3xl">{{ t('site.notAffiliated') }}</p>
      <p class="m-0">© {{ year }} KeyVerhaus · {{ t('site.tagline') }} · <a :href="appUrl" class="text-ink">{{ t('site.app') }}</a></p>
    </div>
  </footer>
</template>

<script setup lang="ts">
import de from '~/i18n/de'
import en from '~/i18n/en'
import es from '~/i18n/es'
import fr from '~/i18n/fr'
import it from '~/i18n/it'
import pl from '~/i18n/pl'
import uk from '~/i18n/uk'

const { t, lang } = useLang()
const route = useRoute()
const { appUrl } = useRuntimeConfig().public
const year = new Date().getFullYear()
const names = { uk: uk.name, en: en.name, pl: pl.name, de: de.name, fr: fr.name, es: es.name, it: it.name }
// Same page in another language: swap the first path segment, keep the query.
const switchTo = (l: Lang) => ({ path: route.path.replace(/^\/[a-z]{2}(?=\/|$)/, `/${l}`), query: route.query })
</script>
