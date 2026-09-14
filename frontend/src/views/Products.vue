<template>
  <div>
    <el-card shadow="never">
      <el-table :data="products" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="产品名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sku" label="SKU" width="120" />
        <el-table-column prop="category_name" label="分类" width="100" />
        <el-table-column label="售价" width="100">
          <template #default="{ row }">¥{{ row.current_price }}</template>
        </el-table-column>
        <el-table-column label="毛利率" width="100">
          <template #default="{ row }">
            <el-tag :type="row.margin_percent >= 40 ? 'success' : row.margin_percent >= 30 ? 'warning' : 'danger'" size="small">
              {{ row.margin_percent }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sales_month" label="月销" width="90" sortable />
        <el-table-column prop="stock_quantity" label="库存" width="90" sortable />
        <el-table-column label="评分" width="90">
          <template #default="{ row }">⭐ {{ row.rating }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 产品详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="detail?.product?.name || '产品详情'" size="480px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="售价">¥{{ detail.product.current_price }}</el-descriptions-item>
          <el-descriptions-item label="成本">¥{{ detail.product.cost_price }}</el-descriptions-item>
          <el-descriptions-item label="毛利率">{{ detail.product.margin_percent }}%</el-descriptions-item>
          <el-descriptions-item label="月销">{{ detail.product.sales_month }}</el-descriptions-item>
          <el-descriptions-item label="库存">{{ detail.product.stock_quantity }}</el-descriptions-item>
          <el-descriptions-item label="评分">{{ detail.product.rating }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 18px">竞品价格</h4>
        <el-table :data="detail.product.competitors || []" size="small">
          <el-table-column prop="name" label="竞品" />
          <el-table-column prop="platform" label="平台" width="80" />
          <el-table-column label="价格" width="90">
            <template #default="{ row }">
              <span :style="{ color: row.price < detail.product.current_price ? '#f56c6c' : '#67c23a' }">
                ¥{{ row.price }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <h4 style="margin-top: 18px">价格历史</h4>
        <el-timeline v-if="(detail.product.price_history || []).length">
          <el-timeline-item
            v-for="(h, i) in detail.product.price_history"
            :key="i"
            :timestamp="h.created_at"
          >
            {{ h.old_price }} → ¥{{ h.new_price }}（{{ h.change_type }}）
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无价格调整记录" :image-size="60" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const products = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const detail = ref(null)

async function loadProducts() {
  loading.value = true
  try {
    const res = await api.get('/products')
    products.value = res.data.products || []
  } catch (e) {
    ElMessage.error('加载产品失败：' + (e.message || ''))
  } finally {
    loading.value = false
  }
}

async function openDetail(id) {
  try {
    const res = await api.get(`/products/${id}`)
    detail.value = res.data
    drawerVisible.value = true
  } catch (e) {
    ElMessage.error('加载详情失败：' + (e.message || ''))
  }
}

onMounted(loadProducts)
</script>
