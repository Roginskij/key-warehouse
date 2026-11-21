import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/stores/session'

const CATALOG = ['catalog.view', 'catalog.edit', 'catalog.moderate', 'catalog.import']

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    // "/" itself: logged-in users go to stock, everyone else ends up on login (guard below).
    // Must come first, otherwise the layout routes below match "/" and render an empty page.
    { path: '/', name: 'home', redirect: { name: 'stock' } },
    {
      path: '/',
      component: () => import('@/layouts/AuthLayout.vue'),
      meta: { guest: true },
      children: [
        { path: 'login', name: 'login', component: () => import('@/pages/auth/LoginPage.vue') },
        { path: 'register', name: 'register', component: () => import('@/pages/auth/RegisterPage.vue') },
        { path: 'check-email', name: 'check-email', component: () => import('@/pages/auth/CheckEmailPage.vue') },
        { path: 'forgot-password', name: 'forgot', component: () => import('@/pages/auth/ForgotPage.vue') },
      ],
    },
    // Links from e-mails work whether you are logged in or not.
    {
      path: '/',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        { path: 'verify-email', name: 'verify', component: () => import('@/pages/auth/VerifyEmailPage.vue') },
        { path: 'reset-password', name: 'reset', component: () => import('@/pages/auth/ResetPage.vue') },
        { path: 'invite', name: 'invite', component: () => import('@/pages/auth/InvitePage.vue') },
        { path: 'staff-invite', name: 'staff-invite', component: () => import('@/pages/auth/StaffInvitePage.vue') },
      ],
    },
    {
      path: '/',
      component: () => import('@/layouts/AppShell.vue'),
      meta: { auth: true, app: true },
      children: [
        { path: 'stock', name: 'stock', component: () => import('@/pages/app/StockPage.vue') },
        { path: 'stock/new', name: 'item-new', component: () => import('@/pages/app/ItemFormPage.vue') },
        { path: 'stock/:id', name: 'item', component: () => import('@/pages/app/ItemPage.vue'), props: true },
        { path: 'stock/:id/edit', name: 'item-edit', component: () => import('@/pages/app/ItemFormPage.vue'), props: true },
        { path: 'reorder', name: 'reorder', component: () => import('@/pages/app/ReorderPage.vue') },
        { path: 'locations/labels', name: 'labels', component: () => import('@/pages/app/LabelsPage.vue') },
        { path: 'l/:wid/:lid', name: 'sticker', component: () => import('@/pages/app/StickerPage.vue'), props: true },
        { path: 'locations', name: 'locations', component: () => import('@/pages/app/LocationsPage.vue') },
        { path: 'import', name: 'import', component: () => import('@/pages/app/ImportPage.vue') },
        { path: 'more', name: 'more', component: () => import('@/pages/app/MorePage.vue') },
        { path: 'team', name: 'team', component: () => import('@/pages/app/TeamPage.vue') },
        { path: 'public-profile', name: 'public-profile', component: () => import('@/pages/app/PublicProfilePage.vue') },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { auth: true, admin: true },
      children: [
        { path: '', name: 'admin', component: () => import('@/pages/admin/OverviewPage.vue') },
        { path: 'catalog', name: 'admin-catalog', component: () => import('@/pages/admin/CatalogPage.vue'), meta: { perms: CATALOG } },
        { path: 'catalog/new', name: 'admin-item-new', component: () => import('@/pages/admin/CatalogNewPage.vue'), meta: { perms: ['catalog.edit'] } },
        { path: 'catalog/:id', name: 'admin-item', component: () => import('@/pages/admin/CatalogItemPage.vue'), props: true, meta: { perms: CATALOG } },
        { path: 'proposals', name: 'admin-proposals', component: () => import('@/pages/admin/ProposalsPage.vue'), meta: { perms: CATALOG } },
        { path: 'import', name: 'admin-import', component: () => import('@/pages/admin/CatalogImportPage.vue'), meta: { perms: ['catalog.import'] } },
        { path: 'brands', name: 'admin-brands', component: () => import('@/pages/admin/BrandsPage.vue'), meta: { perms: CATALOG } },
        { path: 'attributes', name: 'admin-attributes', component: () => import('@/pages/admin/AttributesPage.vue'), meta: { perms: ['catalog.attributes'] } },
        { path: 'history', name: 'admin-history', component: () => import('@/pages/admin/HistoryPage.vue'), meta: { perms: CATALOG } },
        { path: 'users', name: 'admin-users', component: () => import('@/pages/admin/UsersPage.vue'), meta: { perms: ['users.view'] } },
        { path: 'workshops', name: 'admin-workshops', component: () => import('@/pages/admin/WorkshopsPage.vue'), meta: { perms: ['workshops.view'] } },
        { path: 'workshops/:id', name: 'admin-workshop', component: () => import('@/pages/admin/WorkshopPage.vue'), props: true, meta: { perms: ['workshops.view'] } },
        { path: 'waitlist', name: 'admin-waitlist', component: () => import('@/pages/admin/WaitlistPage.vue'), meta: { perms: ['users.view'] } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const session = useSession()
  if (!session.loaded) await session.load()
  if (to.matched.some((r) => r.meta.auth) && !session.isLoggedIn) {
    // Remember where the user wanted to go, unless it is just the start page.
    return { name: 'login', query: ['/', '/stock'].includes(to.fullPath) ? {} : { next: to.fullPath } }
  }
  if (to.matched.some((r) => r.meta.guest) && session.isLoggedIn) return { name: 'stock' }
  if (to.matched.some((r) => r.meta.admin) && !session.isAdmin) return { name: 'stock' }
  // KeyVerhaus staff have no workshop: the stock part is not for them, the admin is home.
  // "more" stays open — password, language, own data.
  if (to.matched.some((r) => r.meta.app) && to.name !== 'more' && session.isAdmin && !session.workshops.length) {
    return { name: 'admin' }
  }
  const perms = to.meta.perms as string[] | undefined
  if (perms && !session.can(...perms)) return { name: 'admin' }
})

window.addEventListener('kv:session-expired', () => {
  const session = useSession()
  session.me = null
  router.push({ name: 'login' })
})

export default router
