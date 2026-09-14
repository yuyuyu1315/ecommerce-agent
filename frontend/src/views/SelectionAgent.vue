<template>
  <div>
    <!-- 分析输入 -->
    <el-card shadow="never">
      <template #header>选品分析（调用 DeepSeek 真实分析）</template>
      <el-form inline @submit.prevent>
        <el-form-item label="品类关键词">
          <el-input
            v-model="category"
            placeholder="如：连衣裙 / 蓝牙耳机"
            style="width: 220px"
            clearable
            @keyup.enter="runAnalyze"
          />
        </el-form-item>
        <el-form-item label="产品关键词（可选）">
          <el-input
            v-model="productName"
            placeholder="如：碎花"
            style="width: 200px"
            clearable
            @keyup.enter="runAnalyze"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="analyzing" @click="runAnalyze">
            {{ analyzing ? 'AI 分析中…' : '开始分析' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 分析结果 -->
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 8px"
      />
      <el-row v-if="result" :gutter="12" style="margin-top: 12px">
        <el-col :xs="24" :md="8">
          <el-card shadow="hover">
            <div class="result-title">{{ result.product_name }}</div>
            <div class="result-sub">{{ result.category }}</div>
            <div class="result-score">
              置信度
              <el-progress
                type="dashboard"
                :percentage="Math.round((result.confidence_score || 0) * 100)"
                :width="90"
                :color="result.confidence_score >= 0.8 ? '#67c23a' : '#e6a23c'"
              />
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="16">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="预估毛利率">{{ result.estimated_margin }}%</el-descriptions-item>
            <el-descriptions-item label="预估月销">{{ result.estimated_sales }} 件</el-descriptions-item>
            <el-descriptions-item label="预估月销额">¥{{ result.estimated_revenue }}</el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag :type="riskType(result.risk_level)" size="small">{{ riskText(result.risk_level) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="优先级">
              <el-rate :model-value="result.priority" disabled :max="10" />
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag type="info" size="small">{{ result.status }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-card shadow="never" style="margin-top: 12px">
            <template #header>选品理由</template>
            <p class="reason">{{ result.selection_reason }}</p>
            <div style="margin-top: 8px">
              <el-tag v-for="f in result.opportunity_factors" :key="f" type="success" size="small" style="margin: 2px" effect="plain">
                ✓ {{ f }}
              </el-tag>
            </div>
            <div style="margin-top: 6px">
              <el-tag v-for="f in result.risk_factors" :key="f" type="danger" size="small" style="margin: 2px" effect="plain">
                ⚠ {{ f }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史选品记录 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>选品记录</span>
          <el-button size="small" @click="loadSelections">刷新</el-button>
        </div>
      </template>
      <el-table :data="selections" v-loading="selectionsLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="product_name" label="选品" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category" label="品类" width="130" />
        <el-table-column label="置信度" width="100">
          <template #default="{ row }">{{ Math.round(row.confidence_score * 100) }}%</template>
        </el-table-column>
        <el-table-column label="预估毛利" width="100">
          <template #default="{ row }">{{ row.estimated_margin }}%</template>
        </el-table-column>
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="riskType(row.risk_level)" size="small">{{ riskText(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : 'info'" size="small">
              {{ row.status === 'approved' ? '已通过' : '待审批' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'approved'"
              link
              type="primary"
              @click="approve(row.id)"
            >
              通过
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const category = ref('连衣裙')
const productName = ref('')
const analyzing = ref(false)
const result = ref(null)
const error = ref('')
const selections = ref([])
const selectionsLoading = ref(false)

function riskType(level) {
  return level === 'low' ? 'success' : level === 'high' ? 'danger' : 'warning'
}
function riskText(level) {
  return level === 'low' ? '低风险' : level === 'high' ? '高风险' : '中风险'
}

async function runAnalyze() {
  if (!category.value && !productName.value) {
    ElMessage.warning('请输入品类或产品关键词')
    return
  }
  analyzing.value = true
  error.value = ''
  try {
    const res = await api.post('/agents/selection/analyze', {
      category: category.value,
      product_name: productName.value,
      params: { user_id: 2 }
    })
    if (res.data.success) {
      result.value = res.data.analysis
      ElMessage.success(`分析完成，已生成选品建议 #${res.data.record_id}`)
    } else {
      error.value = res.data.error || '分析失败'
    }
    loadSelections()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    analyzing.value = false
  }
}

async function loadSelections() {
  selectionsLoading.value = true
  try {
    const res = await api.get('/agents/selection')
    selections.value = res.data.selections || []
  } catch (e) {
    ElMessage.error('加载选品记录失败')
  } finally {
    selectionsLoading.value = false
  }
}

async function approve(id) {
  try {
    const res = await api.post(`/agents/selection/${id}/approve`)
    ElMessage.success(res.data.message || '已通过')
    loadSelections()
  } catch (e) {
    ElMessage.error('审批失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(loadSelections)
</script>

<style scoped>
.result-title {
  font-size: 16px;
  font-weight: 600;
}
.result-sub {
  color: #909399;
  font-size: 13px;
  margin: 4px 0 12px;
}
.result-score {
  text-align: center;
}
.reason {
  margin: 0;
  line-height: 1.7;
  color: #606266;
}
</style>
