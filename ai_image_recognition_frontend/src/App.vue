<template>
  <el-container style="height: 100vh;">
    <el-aside :width="isCollapse ? '64px' : '200px'" class="sidebar-container">
      <div class="logo-container">
        <h3 class="title" v-if="!isCollapse">AI模型<br>标准化迭代系统</h3>
        <h3 class="title-collapsed" v-else>AI</h3>
      </div>
      <el-menu
        :default-active="$route.path"
        class="el-menu-vertical-demo"
        :collapse="isCollapse"
        router
      >
        <el-menu-item index="/">
          <el-icon><home-filled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/model-development">
          <el-icon><cpu /></el-icon>
          <template #title>模型开发</template>
        </el-menu-item>
        <el-menu-item index="/image-annotation">
          <el-icon><picture-filled /></el-icon>
          <template #title>图像标注</template>
        </el-menu-item>
        <el-menu-item index="/evaluation-optimization">
          <el-icon><data-analysis /></el-icon>
          <template #title>评估优化</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
      <div class="collapse-btn" @click="toggleCollapse">
        <el-icon v-if="isCollapse"><arrow-right /></el-icon>
        <el-icon v-else><arrow-left /></el-icon>
      </div>
    </el-aside>
    <el-main class="main-content">
      <router-view></router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import {
  Cpu,
  PictureFilled,
  DataAnalysis,
  ArrowLeft,
  ArrowRight,
  HomeFilled,
  Setting
} from '@element-plus/icons-vue'

const isCollapse = ref(false)

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}
</script>

<style scoped>
.sidebar-container {
  background-color: #ecf5ff;
  position: relative;
  transition: width 0.3s;
  overflow-x: hidden;
  overflow-y: auto;
}

.el-menu {
  background-color: transparent;
  border-right: none;
}

.main-content {
    min-height: 100vh;
    overflow: auto;
    padding: 0;
    box-sizing: border-box;
    
    /* 全局滚动条样式 */
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
  }
}

.title {
  text-align: center;
  padding: 20px 0;
  margin: 0;
}

.title-collapsed {
  text-align: center;
  padding: 20px 0;
  margin: 0;
  font-size: 16px;
}

.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
}

.collapse-btn {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #409eff;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
  z-index: 1;
}
</style>
