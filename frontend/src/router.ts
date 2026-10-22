import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory('/tos'),
  routes: [
    { path: '/', component: () => import('./pages/Home.vue') },
    { path: '/receiving', component: () => import('./pages/ContainerReceiving.vue') },
    { path: '/inventory', component: () => import('./pages/ContainerInventory.vue') },
    { path: '/:path(.*)*', component: () => import('./pages/NotFound.vue') },
    { path: '/relocation', component: () => import('./pages/ContainerRelocation.vue') },
    { path: '/yard', component: () => import('./pages/YardOverview.vue') },
  ],
})
