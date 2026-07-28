<template>
  <div class="matrix-stats">
    <v-card density="compact" variant="outlined">
      <v-card-title class="text-subtitle-2 d-flex align-center">
        <v-icon class="mr-2" size="small">mdi-chart-bar</v-icon>
        统计概览
        <v-spacer />
        <v-btn
          icon
          :loading="loading"
          size="x-small"
          variant="text"
          @click="refreshStats"
        >
          <v-icon size="small">mdi-refresh</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-2">
        <!-- 总体统计 -->
        <div class="stats-overview mb-3">
          <v-row dense>
            <v-col cols="3">
              <div class="stat-card">
                <div class="stat-number text-h5">{{ stats?.total_combinations || 0 }}</div>
                <div class="stat-label text-caption">总组合</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="stat-card">
                <div class="stat-number text-h5 text-success">
                  {{ stats?.owned_combinations || 0 }}
                </div>
                <div class="stat-label text-caption">已拥有</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="stat-card">
                <div class="stat-number text-h5 text-warning">
                  {{ stats?.max_level_combinations || 0 }}
                </div>
                <div class="stat-label text-caption">满级</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="stat-card">
                <div class="stat-number text-h5 text-info">
                  {{ stats?.completion_rate || 0 }}%
                </div>
                <div class="stat-label text-caption">完成度</div>
              </div>
            </v-col>
          </v-row>
        </div>

        <!-- 完成度进度条 -->
        <div class="mb-3">
          <div class="d-flex align-center mb-1">
            <span class="text-caption">总体完成度</span>
            <v-spacer />
            <span class="text-caption font-weight-bold">
              {{ stats?.owned_combinations || 0 }} / {{ stats?.total_combinations || 0 }}
            </span>
          </div>
          <v-progress-linear
            color="primary"
            height="8"
            :model-value="stats?.completion_rate || 0"
            rounded
          />
        </div>

        <v-divider class="my-2" />

        <!-- 按基础属性统计 -->
        <div class="stats-section mb-3">
          <div class="text-caption font-weight-bold mb-2">按基础属性</div>
          <div class="stats-bars">
            <div
              v-for="(data, attrId) in stats?.by_attribute"
              :key="attrId"
              class="stat-bar-item"
            >
              <div class="d-flex align-center mb-1">
                <span class="text-caption">{{ attributeNames[attrId] || attrId }}</span>
                <v-spacer />
                <span class="text-caption text-grey">
                  {{ data.owned }}/{{ data.total }}
                </span>
              </div>
              <v-progress-linear
                color="primary"
                height="6"
                :model-value="data.completion_rate"
                rounded
              />
            </div>
          </div>
        </div>

        <v-divider class="my-2" />

        <!-- 按附加属性统计 -->
        <div class="stats-section mb-3">
          <div class="text-caption font-weight-bold mb-2">按附加属性</div>
          <div class="stats-bars">
            <div
              v-for="(data, secId) in stats?.by_secondary"
              :key="secId"
              class="stat-bar-item"
            >
              <div class="d-flex align-center mb-1">
                <span class="text-caption">{{ secondaryNames[secId] || secId }}</span>
                <v-spacer />
                <span class="text-caption text-grey">
                  {{ data.owned }}/{{ data.total }}
                </span>
              </div>
              <v-progress-linear
                color="secondary"
                height="6"
                :model-value="data.completion_rate"
                rounded
              />
            </div>
          </div>
        </div>

        <v-divider class="my-2" />

        <!-- 按技能属性统计 -->
        <div class="stats-section mb-3">
          <div class="text-caption font-weight-bold mb-2">按技能属性</div>
          <div class="stats-bars">
            <div
              v-for="(data, skillId) in stats?.by_skill"
              :key="skillId"
              class="stat-bar-item"
            >
              <div class="d-flex align-center mb-1">
                <span class="text-caption">{{ skillNames[skillId] || skillId }}</span>
                <v-spacer />
                <span class="text-caption text-grey">
                  {{ data.owned }}/{{ data.total }}
                </span>
              </div>
              <v-progress-linear
                color="accent"
                height="6"
                :model-value="data.completion_rate"
                rounded
              />
            </div>
          </div>
        </div>

        <v-divider class="my-2" />

        <!-- 按武器类型统计 -->
        <div class="stats-section mb-3">
          <div class="text-caption font-weight-bold mb-2">按武器类型</div>
          <div class="stats-bars">
            <div
              v-for="(data, weaponType) in stats?.by_weapon_type"
              :key="weaponType"
              class="stat-bar-item"
            >
              <div class="d-flex align-center mb-1">
                <span class="text-caption">{{ getWeaponTypeName(weaponType) }}</span>
                <v-spacer />
                <span class="text-caption text-grey">
                  {{ data.owned }}/{{ data.total }}
                </span>
              </div>
              <v-progress-linear
                color="info"
                height="6"
                :model-value="data.completion_rate"
                rounded
              />
            </div>
          </div>
        </div>

        <v-divider class="my-2" />

        <!-- 按稀有度统计 -->
        <div class="stats-section">
          <div class="text-caption font-weight-bold mb-2">按稀有度</div>
          <div class="stats-bars">
            <div
              v-for="(data, rarity) in stats?.by_rarity"
              :key="rarity"
              class="stat-bar-item"
            >
              <div class="d-flex align-center mb-1">
                <v-chip
                  class="mr-2"
                  :color="getRarityColor(rarity)"
                  size="x-small"
                >
                  {{ rarity }}
                </v-chip>
                <v-spacer />
                <span class="text-caption text-grey">
                  {{ data.owned }}/{{ data.total }}
                </span>
              </div>
              <v-progress-linear
                :color="getRarityColor(rarity)"
                height="6"
                :model-value="data.completion_rate"
                rounded
              />
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

// ============================================================================
// 类型定义
// ============================================================================

interface MatrixStatsResponse {
  total_combinations: number
  owned_combinations: number
  max_level_combinations: number
  completion_rate: number
  by_attribute: Record<string, { total: number; owned: number; max_level: number; completion_rate: number }>
  by_secondary: Record<string, { total: number; owned: number; max_level: number; completion_rate: number }>
  by_skill: Record<string, { total: number; owned: number; max_level: number; completion_rate: number }>
  by_weapon_type: Record<string, { total: number; owned: number; max_level: number; completion_rate: number }>
  by_rarity: Record<string, { total: number; owned: number; max_level: number; completion_rate: number }>
}

// ============================================================================
// Props
// ============================================================================

defineProps<{
  attributeNames: Record<string, string>
  secondaryNames: Record<string, string>
  skillNames: Record<string, string>
}>()

// ============================================================================
// 状态
// ============================================================================

const loading = ref(false)
const stats = ref<MatrixStatsResponse | null>(null)

// ============================================================================
// 方法
// ============================================================================

async function fetchStats() {
  loading.value = true
  try {
    const response = await fetch('/api/profiles/matrix_stats')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    stats.value = await response.json()
  } catch (error) {
    console.error('Failed to fetch matrix stats:', error)
  } finally {
    loading.value = false
  }
}

async function refreshStats() {
  await fetchStats()
}

function getWeaponTypeName(type: string): string {
  const names: Record<string, string> = {
    SWORD: '单手剑',
    CLAYM: '双手剑',
    LANCE: '长柄武器',
    PISTOL: '手铳',
    WAND: '施术单元',
  }
  return names[type] || type
}

function getRarityColor(rarity: string): string {
  const colors: Record<string, string> = {
    '3star': 'blue',
    '4star': 'purple',
    '5star': 'orange',
    '6star': 'red',
  }
  return colors[rarity] || 'grey'
}

// ============================================================================
// 生命周期
// ============================================================================

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.matrix-stats {
  width: 100%;
}

.stats-overview {
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
  padding: 8px;
}

.stat-card {
  text-align: center;
  padding: 8px;
}

.stat-number {
  font-weight: bold;
  line-height: 1.2;
}

.stat-label {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.stats-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stats-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-bar-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
