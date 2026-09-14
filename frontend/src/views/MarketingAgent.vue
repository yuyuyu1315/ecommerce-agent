<template>
  <div>
    <!-- 活动选择与分析 -->
    <el-card shadow="never">
      <template #header>营销策划（调用 DeepSeek 生成方案 + 文案并落库）</template>
      <el-form inline @submit.prevent>
        <el-form-item label="选择活动">
          <el-select v-model="campaignId" placeholder="选择要策划的活动" style="width: 300px">
            <el-option
              v-for="c in campaigns"
              :key="c.id"
              :value="c.id"
              :label="`#${c.id} ${c.name}（${c.duration_display}，${c.discount_display}）`"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="analyzing" :disabled="!campaignId" @click="runAnalyze">
            {{ analyzing ? 'AI 策划中…' : '开始策划' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    </el-card>

    <!-- 策划结果 -->
    <el-card v-if="plan" shadow="hover" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <span style="font-weight: 600">📋 {{ plan.theme }}</span>
          <el-tag v-if="campaignAfter" type="success" size="small">活动状态：{{ statusText(campaignAfter.status) }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="目标">{{ plan.objective }}</el-descriptions-item>
        <el-descriptions-item label="目标人群">{{ plan.target_audience }}</el-descriptions-item>
        <el-descriptions-item label="促销策略">{{ plan.discount_strategy }}</el-descriptions-item>
        <el-descriptions-item label="节奏安排">{{ plan.timeline }}</el-descriptions-item>
      </el-descriptions>
      <el-row :gutter="12" style="margin-top: 12px">
        <el-col :xs="24" :md="12">
          <h4>渠道与预算分配</h4>
          <el-progress
            v-for="(v, k) in plan.budget_allocation"
            :key="k"
            :percentage="budgetPercent(v)"
            :format="() => `${k}：¥${Number(v).toLocaleString()}`"
            style="margin: 6px 0"
          />
          <div style="margin-top: 8px">
            <el-tag v-for="r in plan.risks" :key="r" type="danger" size="small" effect="plain" style="margin: 2px">
              ⚠ {{ r }}
            </el-tag>
          </div>
        </el-col>
        <el-col :xs="24" :md="12">
          <h4>KPI</h4>
          <div v-for="(v, k) in plan.kpis" :key="k" style="padding: 4px 0">
            <b>{{ k }}</b>：{{ v }}
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 生成的营销文案 -->
    <el-card v-if="contents.length" shadow="never" style="margin-top: 16px">
      <template #header>AI 生成的营销文案（{{ contents.length }} 条）</template>
      <el-row :gutter="12">
        <el-col v-for="(c, i) in contents" :key="i" :xs="24" :md="8" style="margin-bottom: 12px">
          <el-card shadow="hover" class="content-card">
            <div style="display: flex; justify-content: space-between; align-items: center">
              <el-tag size="small" type="primary">{{ c.content_type }}</el-tag>
              <span style="color: #909399; font-size: 12px">{{ c.platform }} · {{ c.tone }}</span>
            </div>
            <h4 style="margin: 10px 0 6px">{{ c.title }}</h4>
            <p class="content-text">{{ c.content }}</p>
            <div>
              <el-tag v-for="h in c.hashtags" :key="h" size="small" effect="plain" style="margin: 2px">#{{ h }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 活动列表 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>营销活动</span>
          <el-button size="small" @click="loadCampaigns">刷新</el-button>
        </div>
      </template>
      <el-table :data="campaigns" v-loading="campaignsLoading" @row-click="loadDetail">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="活动名称" min-width="140" />
        <el-table-column prop="campaign_type" label="类型" width="100" />
        <el-table-column prop="duration_display" label="周期" width="90" />
        <el-table-column prop="discount_display" label="促销" min-width="120" />
        <el-table-column label="预算" width="100">
          <template #default="{ row }">¥{{ row.budget?.toLocaleString?.() ?? row.budget }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'planning' ? 'warning' : 'info'" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI 文案" width="90">
          <template #default="{ row }">{{ row.contents_count }} 条</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const campaigns = ref([])
const campaignId = ref(null)
const analyzing = ref(false)
const error = ref('')
const plan = ref(null)
const campaignAfter = ref(null)
const contents = ref([])
const campaignsLoading = ref(false)

function statusText(s) {
  return { active: '进行中', planning: '策划中', draft: '草稿', finished: '已结束', paused: '已暂停' }[s] || s
}

async function loadCampaigns() {
  campaignsLoading.value = true
  try {
    const res = await api.get('/agents/marketing/campaigns')
    campaigns.value = res.data.campaigns || []
  } catch (e) {
    ElMessage.error('加载活动失败')
  } finally {
    campaignsLoading.value = false
  }
}

async function loadDetail(id) {
  try {
    const res = await api.get(`/agents/marketing/campaigns/${id}`)
    const d = res.data
    plan.value = d.campaign?.strategy_summary ? JSON.parse(d.campaign.strategy_summary) : null
    contents.value = d.contents || []
    campaignAfter.value = d.campaign
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

async function runAnalyze() {
  if (!campaignId.value) return
  analyzing.value = true
  error.value = ''
  try {
    const res = await api.post('/agents/marketing/analyze', {
      campaign_id: campaignId.value,
      params: { user_id: 2 }
    })
    if (res.data.success) {
      plan.value = res.data.plan
      campaignAfter.value = res.data.campaign
      ElMessage.success(`策划完成：${res.data.contents_count} 条文案已生成`)
      loadCampaigns()
      if (res.data.contents_count) {
        const detail = await api.get(`/agents/marketing/campaigns/${campaignId.value}`)
        contents.value = detail.data.contents || []
      }
    } else {
      error.value = res.data.error || '策划失败'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    analyzing.value = false
  }
}

function budgetPercent(v) {
  const total = Object.values(plan.value?.budget_allocation || {}).reduce((a, b) => a + Number(b || 0), 0)
  return total ? Math.round((Number(v) / total) * 100) : 0
}

onMounted(() => {
  loadCampaigns()
})
</script>

<style scoped>
.content-card :deep(.el-card__body) {
  height: 100%;
}
.content-text {
  color: #606266;
  line-height: 1.7;
  font-size: 13px;
  margin: 0 0 8px;
  min-height: 60px;
}
</style>
