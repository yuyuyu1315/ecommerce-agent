<template>
  <el-container class="app-layout">
    <el-aside width="210px" class="app-aside">
      <div class="logo">
        <el-icon :size="22" color="#409EFF"><ShoppingCart /></el-icon>
        <span>电商运营 Agent</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#001529"
        text-color="#a6adb4"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Goods /></el-icon>
          <span>产品管理</span>
        </el-menu-item>
        <el-menu-item index="/selection">
          <el-icon><MagicStick /></el-icon>
          <span>选品 Agent</span>
        </el-menu-item>
        <el-menu-item index="/rag">
          <el-icon><ChatDotRound /></el-icon>
          <span>知识问答</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <span class="page-title">{{ $route.meta.title }}</span>
        <span class="header-tip">AI 多智能体电商运营平台 · v0.5.0</span>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ChatDotRound, DataBoard, Goods, MagicStick, ShoppingCart } from '@element-plus/icons-vue'
</script>

<style>
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.app-layout {
  height: 100vh;
}

.app-aside {
  background-color: #001529;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 60px;
  padding: 0 16px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.app-aside .el-menu {
  border-right: none;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.header-tip {
  font-size: 13px;
  color: #909399;
}

.app-main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
