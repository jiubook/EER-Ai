<template>
  <!-- 发现新版本 -->
  <v-snackbar v-model="hasNewVersionDialog" vertical>
    <p><strong>发现新版本！</strong></p>
    <p><strong>当前版本：</strong>{{ currentVersion }}</p>
    <p><strong>最新版本：</strong>{{ updateInfo?.latestVersion }}</p>
    <template #actions>
      <v-btn class="ms-2" @click="hasNewVersionDialog = false">稍后提醒</v-btn>
      <v-btn
        class="ms-2"
        color="primary"
        :loading="isUpdating"
        variant="elevated"
        @click="installUpdate"
        >一键更新</v-btn
      >
    </template>
  </v-snackbar>

  <!-- 已是最新版本 -->
  <v-snackbar v-model="isLatestVersionDialog" color="info">
    <strong>已是最新版本：</strong>{{ currentVersion }}
    <template #actions>
      <v-btn text @click="isLatestVersionDialog = false">关闭</v-btn>
    </template>
  </v-snackbar>

  <!-- 检查更新失败 -->
  <v-snackbar v-model="checkUpdateFailedDialog" color="error">
    <strong>检查更新失败：</strong>{{ updateErrorMessage }}
    <template #actions>
      <v-btn text @click="checkUpdateFailedDialog = false">关闭</v-btn>
    </template>
  </v-snackbar>

  <!-- 更新进度 -->
  <v-dialog v-model="updateProgressDialog" max-width="500" persistent>
    <v-card>
      <v-card-title>更新下载</v-card-title>
      <v-card-text>
        <div class="mb-4">
          <div class="d-flex justify-space-between mb-2">
            <span>{{ currentVersion }} → {{ updateInfo?.latestVersion }}</span>
            <span>{{ formatSize(downloadedSize) }} / {{ formatSize(totalSize) }}</span>
          </div>
          <v-progress-linear
            color="primary"
            height="20"
            :model-value="downloadProgress"
          >
            <template #default>
              <strong>{{ downloadProgress.toFixed(1) }}%</strong>
            </template>
          </v-progress-linear>
          <div class="text-center mt-2 text-caption">
            {{ formatSpeed(downloadSpeed) }}
          </div>
        </div>

        <v-select
          v-model="selectedMirror"
          class="mb-3"
          density="comfortable"
          hide-details
          :items="mirrorOptions"
          label="下载源"
          variant="outlined"
        >
          <template #append-inner>
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
              </template>
              <span>当前选择: {{ selectedMirrorName }}</span>
            </v-tooltip>
          </template>
        </v-select>

        <v-expansion-panels v-model="showProxyInput" class="mb-3" flat>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <div class="d-flex align-center">
                <span>使用代理</span>
                <v-spacer />
                <v-switch
                  v-model="proxyEnabled"
                  class="ms-4"
                  color="primary"
                  density="compact"
                  hide-details
                  @click.stop
                />
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-text-field
                v-model="proxyPort"
                class="mb-2"
                density="comfortable"
                :disabled="!proxyEnabled"
                hide-details
                label="代理端口"
                placeholder="7890"
                type="number"
                variant="outlined"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancelDownload">取消</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useUpdateChecker } from '@/composables/useUpdateChecker'

const {
  hasNewVersionDialog,
  isLatestVersionDialog,
  checkUpdateFailedDialog,
  currentVersion,
  updateInfo,
  updateErrorMessage,
  isUpdating,
  updateProgressDialog,
  downloadProgress,
  downloadSpeed,
  downloadedSize,
  totalSize,
  selectedMirror,
  proxyEnabled,
  proxyPort,
  showProxyInput,
  installUpdate,
  cancelDownload,
} = useUpdateChecker()

const mirrorOptions = ref<Array<{ title: string; value: string }>>([])

const selectedMirrorName = computed(() => {
  const mirror = mirrorOptions.value.find((m) => m.value === selectedMirror.value)
  return mirror ? mirror.title : 'GitHub 官方'
})

onMounted(async () => {
  try {
    const response = await fetch('/api/update/mirrors')
    const data = await response.json()
    mirrorOptions.value = data.mirrors
  } catch (error) {
    console.error('获取镜像源列表失败：', error)
    mirrorOptions.value = [{ title: 'GitHub 官方', value: 'github' }]
  }
})

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

function formatSpeed(bytesPerSecond: number): string {
  return formatSize(bytesPerSecond) + '/s'
}
</script>
