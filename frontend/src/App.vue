<template>
  <v-app>
    <!-- 加载状态 -->
    <v-overlay v-model="isLoading" class="align-center justify-center" persistent>
      <v-progress-circular color="primary" indeterminate size="64" />
      <div class="text-h6 mt-4">正在加载...</div>
    </v-overlay>

    <!-- 错误提示 -->
    <v-dialog v-model="showError" max-width="500" persistent>
      <v-card>
        <v-card-title class="text-h5 text-error">加载失败</v-card-title>
        <v-card-text>
          <p>{{ errorMessage }}</p>
          <p class="text-caption mt-2">请确保后端服务正在运行。</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="retryInit">重试</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-navigation-drawer v-model="drawer">
      <v-card class="pa-4" rounded="0" to="/" variant="flat">
        <logo class="d-block mb-4 w-50 h-auto mx-auto" />
        <h1 class="text-center ma-4">终末地基质<br />妙妙小工具</h1>
      </v-card>
      <v-divider />
      <v-list density="comfortable" nav>
        <v-list-item
          v-for="(routeItem, index) in router.options.routes"
          :key="index"
          color="primary"
          :prepend-icon="(routeItem.meta as any)?.icon"
          :to="routeItem.path"
        >
          {{ routeItem.meta?.title ?? routeItem.name }}
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar app color="primary" density="comfortable" flat>
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-app-bar-title>{{ route.meta?.title || '终末地基质妙妙小工具' }}</v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-update" @click="checkForUpdates(true)" />
        <v-btn icon="mdi-theme-light-dark" @click="theme.toggle()" />
      </template>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <!-- 更新提示 -->
    <UpdateDialogs />
  </v-app>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import Logo from '@/components/icons/logo.vue'
import UpdateDialogs from '@/components/UpdateDialogs.vue'
import { useLogs } from '@/composables/useLogs'
import { useUpdateChecker } from '@/composables/useUpdateChecker'
import { useStaticData } from '@/utils/gameData/staticData'

const route = useRoute()
const router = useRouter()
const theme = useTheme()

const drawer = ref<boolean | null>(null)
const isLoading = ref(true)
const showError = ref(false)
const errorMessage = ref('')

// 初始化日志 WebSocket 连接
useLogs()

// 检查更新
const { checkForUpdates } = useUpdateChecker()

const { fetchStaticData } = useStaticData()

async function initApp() {
  try {
    isLoading.value = true
    showError.value = false

    // 初始化游戏数据
    await fetchStaticData()

    // 初始检查更新（不阻塞）
    checkForUpdates(false).catch(err => {
      console.warn('检查更新失败，但不影响应用使用:', err)
    })

    isLoading.value = false
  } catch (error) {
    console.error('应用初始化失败:', error)
    errorMessage.value = error instanceof Error ? error.message : '未知错误'
    showError.value = true
    isLoading.value = false
  }
}

function retryInit() {
  initApp()
}

onMounted(() => {
  initApp()
})
</script>

<style scoped lang="scss"></style>
