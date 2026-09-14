<template>
  <div>
    <!-- 分析输入 -->
    <el-card shadow="never">
      <template #header>定价分析（调用 DeepSeek 结合竞品/成本/评价分析）</template>
      <el-form inline @submit.prevent>
        <el-form-item label="选择产品">
          <el-select
            v-model="productId"
            filterable
            placeholder="选择要分析的产品"
            style="width: 320px"
          >
            <el-option
              v-for="p in products"
              :key="p.id"
              :value="p.id"
              :label="`#${p.id} ${p.name}（现价 ¥${p.current_price} / 成本 ¥${p.cost_price}）`"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="analyzing" :disabled="!productId" @click="runAnalyze">
            {{ analyzing ? 'AI 分析中…' : '开始定价分析' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 8px"
      />
    </el-card>

    <!-- 定价建议记录 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>定价建议记录</span>
          <div>
            <el-radio-group v-model="statusFilter" size="small" @change="loadSuggestions">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button value="pending">待审批</el-radio-button>
              <el-radio-button value="approved">已通过</el-radio-button>
              <el-radio-button value="rejected">已驳回</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      <el-table :data="suggestions" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="product_name" label="产品" min-width="180" show-overflow-tooltip />
        <el-table-column label="现价" width="90">
          <template #default="{ row }">¥{{ row.current_price }}</template>
        </el-table-column>
        <el-table-column label="建议价" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.recommended_price !== row.current_price ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              ¥{{ row.recommended_price }}
            </span>
            <span v-if="row.price_change_percent" style="color: #909399; font-size: 12px">
              ({{ row.price_change_percent > 0 ? '+' : '' }}{{ row.price_change_percent }}%)
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="strategy" label="策略" width="110" />
        <el-table-column label="毛利率" width="90">
          <template #default="{ row }">{{ row.margin_percent_after }}%</template>
        </el-table-column>
        <el-table-column label="置信度" width="90">
          <template #default="{ row }">{{ Math.round(row.confidence_score * 100) }}%</template>
        </el-table-column>
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="riskType(row.risk_level)" size="small">{{ riskText(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
              {{ row.status === 'approved' ? '已通过' : row.status === 'rejected' ? '已驳回' : '待审批' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button link type="success" @click="approve(row.id)">通过并应用</el-button>
              <el-button link type="danger" @click="reject(row.id)">驳回</el-button>
            </template>
            <el-button v-else link type="primary" @click="showReason(row)">理由</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const products = ref([])
const productId = ref(null)
const analyzing = ref(false)
const error = ref('')
const suggestions = ref([])
const loading = ref(false)
const statusFilter = ref('')

function riskType(level) {
  return level === 'low' ? 'success' : level === 'high' ? 'danger' : 'warning'
}
function riskText(level) {
  return level === 'low' ? '低' : level === 'high' ? '高' : '中'
}

async function loadProducts() {
  try {
    const res = await api.get('/products')
    products.value = res.data.products || []
  } catch (e) {
    ElMessage.error('加载产品失败')
  }
}

async function runAnalyze() {
  if (!productId.value) return
  analyzing.value = true
  error.value = ''
  try {
    const res = await api.post('/agents/pricing/analyze', {
      product_id: productId.value,
      params: { user_id: 2 }
    })
    if (res.data.success) {
      const s = res.data.suggestion
      ElMessageBox.alert(
        `AI 建议：¥${s.current_price} → ¥${s.recommended_price}（${s.strategy}，置信度 ${Math.round(s.confidence_score * 100)}%）\n\n${s.reason}`,
        '定价建议',
        { confirmButtonText: '知道了' }
      )
    } else {
      error.value = res.data.error || '分析失败'
    }
    loadSuggestions()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    analyzing.value = false
  }
}

async function loadSuggestions() {
  loading.value = true
  try {
    const res = await api.get('/agents/pricing', { params: { status: statusFilter.value || undefined } })
    suggestions.value = res.data.suggestions || []
  } catch (e) {
    ElMessage.error('加载定价记录失败')
  } finally {
    loading.value = false
  }
}

async function approve(id) {
  try {
    const res = await api.post(`/agents/pricing/${id}/approve`)
    ElMessage.success(res.data.message || '已通过')
    loadSuggestions()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

async function reject(id) {
  try {
    const res = await api.post(`/agents/pricing/${id}/reject`)
    ElMessage.success(res.data.message || '已驳回')
    loadSuggestions()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

function showReason(row) {
  ElMessageBox.alert(row.reason || '（无理由）', `定价理由 · ${row.product_name}`, {
    confirmButtonText: '知道了'
  })
}

onMounted(() => {
  loadProducts()
  loadSuggestions()
})
</script>
