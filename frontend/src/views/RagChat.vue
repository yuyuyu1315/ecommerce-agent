<template>
  <el-card shadow="never" style="display: flex; flex-direction: column; height: calc(100vh - 140px)">
    <template #header>
      <div style="display: flex; align-items: center; gap: 10px">
        <span>知识库问答（RAG：向量检索 + DeepSeek 带来源回答）</span>
        <el-button size="small" :loading="rebuilding" @click="rebuildIndex">重建索引</el-button>
      </div>
    </template>

    <!-- 消息列表 -->
    <div ref="listRef" class="chat-list">
      <div v-if="!messages.length" class="chat-empty">
        <el-empty description="输入问题开始对话，例如：如何做好电商选品？" :image-size="80" />
      </div>
      <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
        <div class="msg-bubble">
          <div class="msg-text" v-html="renderText(m.content)"></div>
          <div v-if="m.sources && m.sources.length" class="msg-sources">
            <el-tag
              v-for="s in m.sources"
              :key="s.id"
              size="small"
              type="info"
              effect="plain"
              style="margin: 2px"
            >
              📄 {{ s.title }} · {{ Math.round(s.score * 100) }}%
            </el-tag>
          </div>
        </div>
      </div>
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-bubble msg-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          DeepSeek 正在结合资料回答…
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input">
      <el-input
        v-model="question"
        type="textarea"
        :rows="2"
        placeholder="输入运营问题，回车发送（Shift+Enter 换行）"
        @keydown.enter.exact.prevent="send"
      />
      <el-button type="primary" :loading="loading" style="margin-top: 8px; align-self: flex-end" @click="send">
        发送
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import api from '../api'

const messages = ref([])
const question = ref('')
const loading = ref(false)
const rebuilding = ref(false)
const listRef = ref(null)

function renderText(text) {
  return String(text || '')
    .replace(/\n/g, '<br/>')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
}

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

async function send() {
  const q = question.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  loading.value = true
  scrollToBottom()
  try {
    const res = await api.post('/rag/query', { question: q, top_k: 5 })
    if (res.data.success) {
      messages.value.push({
        role: 'assistant',
        content: res.data.answer,
        sources: res.data.sources
      })
    } else {
      messages.value.push({ role: 'assistant', content: '⚠️ ' + (res.data.error || '查询失败') })
    }
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '⚠️ 请求失败：' + (e.response?.data?.detail || e.message) })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function rebuildIndex() {
  rebuilding.value = true
  try {
    const res = await api.post('/rag/rebuild')
    ElMessage.success(`索引重建完成：共 ${res.data.indexed} 条文档`)
  } catch (e) {
    ElMessage.error('重建失败：' + (e.message || ''))
  } finally {
    rebuilding.value = false
  }
}
</script>

<style scoped>
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
}
.chat-empty {
  display: flex;
  justify-content: center;
  margin-top: 60px;
}
.msg-row {
  display: flex;
  margin-bottom: 14px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.7;
  font-size: 14px;
}
.msg-row.user .msg-bubble {
  background: #409eff;
  color: #fff;
}
.msg-row.assistant .msg-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  color: #303133;
}
.msg-text :deep(b) {
  font-weight: 600;
}
.msg-sources {
  margin-top: 8px;
}
.msg-loading {
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}
.chat-input {
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e4e7ed;
  padding-top: 12px;
}
</style>
