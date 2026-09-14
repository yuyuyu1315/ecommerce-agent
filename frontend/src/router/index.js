import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '数据看板' }
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('../views/Products.vue'),
    meta: { title: '产品管理' }
  },
  {
    path: '/selection',
    name: 'selection',
    component: () => import('../views/SelectionAgent.vue'),
    meta: { title: '选品 Agent' }
  },
  {
    path: '/rag',
    name: 'rag',
    component: () => import('../views/RagChat.vue'),
    meta: { title: '知识问答' }
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
