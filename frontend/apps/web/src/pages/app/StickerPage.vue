<template>
  <div class="flex flex-1 items-center justify-center p-4">
    <UIEmpty v-if="foreign" icon="pin" :title="t('sticker.foreignTitle')" :text="t('sticker.foreignText')">
      <RouterLink :to="{ name: 'stock' }" :class="buttonClass('primary', 'md')">{{ t('nav.stock') }}</RouterLink>
    </UIEmpty>
  </div>
</template>

<script setup lang="ts">
import { buttonClass, UIEmpty } from '@kv/ui'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useSession } from '@/stores/session'

/** A scanned box sticker: open the stock of that place (switching workshop if needed). */
const props = defineProps<{ wid: string; lid: string }>()
const { t } = useI18n()
const router = useRouter()
const session = useSession()
const foreign = ref(false)

onMounted(() => {
  if (!session.workshops.some((w) => w.workshop_id === props.wid)) {
    foreign.value = true
    return
  }
  session.selectWorkshop(props.wid)
  router.replace({ name: 'stock', query: { location: props.lid } })
})
</script>
