<template>
  <div class="matrix-legend">
    <v-card density="compact" variant="outlined">
      <v-card-text class="pa-2">
        <div class="legend-title text-caption font-weight-bold mb-2">
          图例
        </div>

        <div class="legend-items">
          <!-- 颜色图例 -->
          <div class="legend-section">
            <div class="text-caption text-grey mb-1">颜色等级</div>
            <div class="legend-colors">
              <div class="legend-item">
                <div class="legend-color cell-empty" />
                <span class="text-caption">未拥有</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-1" />
                <span class="text-caption">Lv.1</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-2" />
                <span class="text-caption">Lv.2</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-3" />
                <span class="text-caption">Lv.3</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-4" />
                <span class="text-caption">Lv.4</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-5" />
                <span class="text-caption">Lv.5</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-level-6" />
                <span class="text-caption">Lv.6</span>
              </div>
              <div class="legend-item">
                <div class="legend-color cell-max-level" />
                <span class="text-caption">满级</span>
              </div>
            </div>
          </div>

          <v-divider class="my-2" />

          <!-- 稀有度图例 -->
          <div class="legend-section">
            <div class="text-caption text-grey mb-1">武器稀有度</div>
            <div class="legend-rarities">
              <v-chip color="blue" size="x-small">3★</v-chip>
              <v-chip color="purple" size="x-small">4★</v-chip>
              <v-chip color="orange" size="x-small">5★</v-chip>
              <v-chip color="red" size="x-small">6★</v-chip>
            </div>
          </div>

          <v-divider class="my-2" />

          <!-- 编码格式说明 -->
          <div class="legend-section">
            <div class="text-caption text-grey mb-1">编码格式</div>
            <div class="legend-code-format">
              <div class="code-example">
                <span class="code-char attr">X</span>
                <span class="code-char sec">Y</span>
                <span class="code-char skill">Z</span>
                <span class="code-char level">A</span>
                <span class="code-char level">B</span>
                <span class="code-char level">C</span>
              </div>
              <div class="code-labels text-caption">
                <span class="attr">基础</span>
                <span class="sec">附加</span>
                <span class="skill">技能</span>
                <span class="level">等级</span>
              </div>
            </div>
          </div>

          <!-- 统计信息 -->
          <div v-if="stats" class="legend-section mt-2">
            <div class="text-caption text-grey mb-1">统计信息</div>
            <div class="legend-stats">
              <div class="stat-item">
                <span class="stat-label">总组合:</span>
                <span class="stat-value">{{ stats.total }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已拥有:</span>
                <span class="stat-value text-success">{{ stats.owned }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">满级:</span>
                <span class="stat-value text-warning">{{ stats.max_level }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">完成度:</span>
                <span class="stat-value text-info">{{ stats.completion_rate }}%</span>
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
// ============================================================================
// Props
// ============================================================================

defineProps<{
  stats?: {
    total: number
    owned: number
    max_level: number
    completion_rate: number
  } | null
}>()
</script>

<style scoped>
.matrix-legend {
  width: 100%;
}

.legend-title {
  color: rgba(var(--v-theme-on-surface), 0.8);
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.legend-colors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(var(--v-border-color), 0.24);
}

.legend-rarities {
  display: flex;
  gap: 8px;
}

.legend-code-format {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.code-example {
  display: flex;
  gap: 2px;
  font-family: monospace;
  font-size: 14px;
  font-weight: bold;
}

.code-char {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: rgba(var(--v-theme-surface-variant), 0.5);
}

.code-char.attr { color: rgb(var(--v-theme-primary)); }
.code-char.sec { color: rgb(var(--v-theme-secondary)); }
.code-char.skill { color: rgb(var(--v-theme-accent)); }
.code-char.level { color: rgba(var(--v-theme-on-surface), 0.6); }

.code-labels {
  display: flex;
  gap: 2px;
}

.code-labels span {
  width: 20px;
  text-align: center;
  font-size: 10px;
}

.code-labels .attr { color: rgb(var(--v-theme-primary)); }
.code-labels .sec { color: rgb(var(--v-theme-secondary)); }
.code-labels .skill { color: rgb(var(--v-theme-accent)); }
.code-labels .level { color: rgba(var(--v-theme-on-surface), 0.6); }

.legend-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-label {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.stat-value {
  font-weight: bold;
}

/* 颜色等级样式 */
.cell-empty { background: rgba(var(--v-theme-surface-variant), 0.3); }
.cell-level-1 { background: rgba(var(--v-theme-info), 0.1); }
.cell-level-2 { background: rgba(var(--v-theme-info), 0.2); }
.cell-level-3 { background: rgba(var(--v-theme-info), 0.3); }
.cell-level-4 { background: rgba(var(--v-theme-info), 0.4); }
.cell-level-5 { background: rgba(var(--v-theme-info), 0.5); }
.cell-level-6 { background: rgba(var(--v-theme-info), 0.6); }
.cell-max-level {
  background: rgba(var(--v-theme-warning), 0.2);
  box-shadow: inset 0 0 0 2px rgba(var(--v-theme-warning), 0.5);
}
</style>
