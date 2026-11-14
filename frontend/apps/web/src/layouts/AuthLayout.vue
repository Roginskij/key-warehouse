<template>
  <div class="min-h-dvh bg-surface sm:bg-ground">
    <div class="mx-auto flex min-h-dvh max-w-md flex-col px-5 py-5 sm:py-10">
      <header class="mb-6 flex items-center justify-between">
        <RouterLink to="/" class="no-underline"><Logo /></RouterLink>
        <LangSwitch />
      </header>
      <main class="flex flex-1 flex-col sm:flex-none sm:rounded-card sm:border sm:border-line sm:bg-surface sm:p-7">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import LangSwitch from '@/components/LangSwitch.vue'
import Logo from '@/components/Logo.vue'
</script>
