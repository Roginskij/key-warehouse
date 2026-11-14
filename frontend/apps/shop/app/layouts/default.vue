<template>
  <div class="flex min-h-dvh flex-col">
    <SiteHeader />
    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-6 md:py-10">
      <slot />
    </main>
    <SiteFooter />
  </div>
</template>
