import { createRouter, createWebHistory } from 'vue-router'
import ModelDevelopment from '../views/ModelDevelopment.vue'
import ImageAnnotation from '../views/ImageAnnotation.vue'
import EvaluationOptimization from '../views/EvaluationOptimization.vue'
import HomePage from '../views/HomePage.vue'
import Settings from '../views/Settings.vue'

const routes = [
  {
    path: '/',
    name: 'HomePage',
    component: HomePage
  },
  {
    path: '/model-development',
    name: 'ModelDevelopment',
    component: ModelDevelopment
  },
  {
    path: '/image-annotation',
    name: 'ImageAnnotation',
    component: ImageAnnotation
  },
  {
    path: '/evaluation-optimization',
    name: 'EvaluationOptimization',
    component: EvaluationOptimization
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router