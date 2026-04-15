import { ref, watch } from 'vue'

export interface UpdateInfo {
  latestVersion: string
  downloadUrl: string
}

const hasNewVersionDialog = ref<boolean>(false)
const isLatestVersionDialog = ref<boolean>(false)
const checkUpdateFailedDialog = ref<boolean>(false)
const updateProgressDialog = ref<boolean>(false)
const isUpdating = ref<boolean>(false)
const currentVersion = ref<string | null>(null)
const updateInfo = ref<UpdateInfo | null>(null)
const updateErrorMessage = ref<string>('')

// 新增状态
const downloadProgress = ref<number>(0)
const downloadSpeed = ref<number>(0)
const downloadedSize = ref<number>(0)
const totalSize = ref<number>(0)
const selectedMirror = ref<string>('github')
const proxyEnabled = ref<boolean>(false)
const proxyPort = ref<string>('7890')
const showProxyInput = ref<boolean>(false)
const downloadFailed = ref<boolean>(false)
const downloadErrorMessage = ref<string>('')

let progressWs: WebSocket | null = null

export function useUpdateChecker() {
  let restartTimer: ReturnType<typeof setTimeout> | null = null
  let isRestarting = false

  // 监听镜像源和代理变化，使用防抖避免多次触发
  watch([selectedMirror, proxyEnabled, proxyPort], async () => {
    if (!isUpdating.value || !updateProgressDialog.value || isRestarting) return

    // 清除之前的定时器
    if (restartTimer) {
      clearTimeout(restartTimer)
    }

    // 500ms 防抖
    restartTimer = setTimeout(async () => {
      isRestarting = true
      await cancelDownloadInternal()
      await new Promise((resolve) => setTimeout(resolve, 1500))
      await installUpdate()
      isRestarting = false
      restartTimer = null
    }, 500)
  })

  /**
   * 检查更新
   * @param showIfLatest 如果已是最新版本，是否显示提示
   */
  async function checkForUpdates(showIfLatest: boolean = false) {
    try {
      // 调用后端 API 检查更新
      const response = await fetch('/api/update/check')
      const result = await response.json()

      if (result.error) {
        updateErrorMessage.value = result.error
        checkUpdateFailedDialog.value = true
        return
      }

      // 获取当前版本
      const versionResponse = await fetch('/api/version')
      currentVersion.value = await versionResponse.json()

      if (result.has_update && result.update_info) {
        updateInfo.value = {
          latestVersion: result.update_info.version,
          downloadUrl: result.update_info.download_url,
        }
        // 如果 API 返回了 CN 镜像，默认使用 CN 镜像
        if (result.update_info.mirrors?.cn?.downloadUrl) {
          selectedMirror.value = 'cn'
        }
        hasNewVersionDialog.value = true
      } else if (showIfLatest) {
        isLatestVersionDialog.value = true
      }
    } catch (error) {
      console.error('检查更新失败：', error)
      updateErrorMessage.value =
        error instanceof Error ? error.message : '网络请求失败，请检查网络连接'
      checkUpdateFailedDialog.value = true
    }
  }

  /**
   * 连接进度 WebSocket
   */
  function connectProgressWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/update/progress`
    progressWs = new WebSocket(wsUrl)

    progressWs.addEventListener('message', (event) => {
      const data = JSON.parse(event.data)
      downloadedSize.value = data.downloaded
      totalSize.value = data.total
      downloadSpeed.value = data.speed
      downloadProgress.value = data.progress
    })

    progressWs.addEventListener('error', () => {
      progressWs?.close()
      progressWs = null
    })
  }

  /**
   * 断开进度 WebSocket
   */
  function disconnectProgressWebSocket() {
    if (progressWs) {
      progressWs.close()
      progressWs = null
    }
  }

  /**
   * 内部取消下载（不关闭对话框，用于重启下载）
   */
  async function cancelDownloadInternal() {
    try {
      const response = await fetch('/api/update/cancel', { method: 'POST' })
      const result = await response.json()
      if (result.success) {
        disconnectProgressWebSocket()
      }
      return result.success
    } catch (error) {
      console.error('取消下载失败：', error)
      return false
    }
  }

  /**
   * 取消下载
   */
  async function cancelDownload() {
    // 先清除定时器，防止 watch 触发重启
    if (restartTimer) {
      clearTimeout(restartTimer)
      restartTimer = null
    }
    isRestarting = false

    try {
      await fetch('/api/update/cancel', { method: 'POST' })
    } catch (error) {
      console.error('取消下载失败：', error)
    } finally {
      disconnectProgressWebSocket()
      updateProgressDialog.value = false
      isUpdating.value = false
    }
  }
  async function installUpdate() {
    try {
      isUpdating.value = true
      downloadFailed.value = false
      downloadErrorMessage.value = ''
      hasNewVersionDialog.value = false
      updateProgressDialog.value = true

      // 保存配置：先 GET 当前配置，合并更新字段后 POST，避免覆盖用户其他设置
      const proxyUrl = proxyEnabled.value ? `http://127.0.0.1:${proxyPort.value}` : ''
      const currentConfigRes = await fetch('/api/config')
      const currentConfig = await currentConfigRes.json()
      currentConfig.update_mirror = selectedMirror.value
      currentConfig.update_proxy = proxyUrl
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig),
      })

      connectProgressWebSocket()

      const response = await fetch('/api/update/install', { method: 'POST' })
      const result = await response.json()

      if (!result.success) {
        disconnectProgressWebSocket()
        downloadFailed.value = true
        downloadErrorMessage.value = result.error || '更新失败'
      }
    } catch (error) {
      disconnectProgressWebSocket()
      downloadFailed.value = true
      downloadErrorMessage.value = error instanceof Error ? error.message : '更新失败'
    } finally {
      isUpdating.value = false
    }
  }

  return {
    // 状态
    hasNewVersionDialog,
    isLatestVersionDialog,
    checkUpdateFailedDialog,
    updateProgressDialog,
    isUpdating,
    currentVersion,
    updateInfo,
    updateErrorMessage,
    downloadProgress,
    downloadSpeed,
    downloadedSize,
    totalSize,
    selectedMirror,
    proxyEnabled,
    proxyPort,
    showProxyInput,
    downloadFailed,
    downloadErrorMessage,
    // 方法
    checkForUpdates,
    installUpdate,
    cancelDownload,
  }
}
