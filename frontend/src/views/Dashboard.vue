<template>
  <div>
    <!-- 指标卡片 -->
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="14">
        <el-card shadow="never">
          <template #header>月销 Top 产品（件）</template>
          <div ref="salesChartRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="10">
        <el-card shadow="never">
          <template #header>产品分类分布</template>
          <div ref="categoryChartRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import api from '../api'

const summary = ref({})
const products = ref([])
const salesChartRef = ref(null)
const categoryChartRef = ref(null)
let salesChart = null
let categoryChart = null

const cards = computed(() => [
  { label: '在售产品', value: summary.value.product_count ?? '-' },
  { label: '产品分类', value: summary.value.category_count ?? '-' },
  { label: '营销活动', value: summary.value.campaign_count ?? '-' },
  { label: '进行中活动', value: summary.value.active_campaigns ?? '-' },
  { label: '知识库文档', value: summary.value.knowledge_count ?? '-' },
  { label: '用户评价', value: summary.value.review_count ?? '-' },
  { label: '选品建议', value: summary.value.selection_count ?? '-' },
  { label: 'Agent 任务', value: summary.value.agent_task_count ?? '-' },
])

async function loadData() {
  try {
    const [s, p] = await Promise.all([
      api.get('/dashboard/summary'),
      api.get('/products')
    ])
    summary.value = s.data.summary || {}
    products.value = p.data.products || []
    renderSalesChart()
    renderCategoryChart()
  } catch (e) {
    ElMessage.error('加载看板失败：' + (e.message || ''))
  }
}

function renderSalesChart() {
  if (!salesChartRef.value) return
  salesChart = salesChart || echarts.init(salesChartRef.value)
  const top = [...products.value].sort((a, b) => b.sales_month - a.sales_month).slice(0, 8)
  salesChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 10, right: 20, top: 30, bottom: 10, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: top.map((p) => (p.name.length > 10 ? p.name.slice(0, 10) + '…' : p.name)),
      axisLabel: { fontSize: 12 }
    },
    series: [
      {
        type: 'bar',
        data: top.map((p) => p.sales_month),
        itemStyle: { color: '#409EFF', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right' }
      }
    ]
  })
}

function renderCategoryChart() {
  if (!categoryChartRef.value) return
  categoryChart = categoryChart || echarts.init(categoryChartRef.value)
  const byCat = {}
  products.value.forEach((p) => {
    const cat = p.category_name || '未分类'
    byCat[cat] = (byCat[cat] || 0) + 1
  })
  categoryChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '68%'],
        center: ['50%', '44%'],
        data: Object.entries(byCat).map(([name, value]) => ({ name, value })),
        label: { formatter: '{b}: {c}' }
      }
    ]
  })
}

function onResize() {
  salesChart && salesChart.resize()
  categoryChart && categoryChart.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  salesChart && salesChart.dispose()
  categoryChart && categoryChart.dispose()
})
</script>

<style scoped>
.stat-card {
  text-align: center;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}
.chart {
  width: 100%;
  height: 380px;
}
</style>
