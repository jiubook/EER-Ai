<template>
  <div class="matrix-filters">
    <v-card density="compact" variant="outlined">
      <v-card-text class="pa-2">
        <v-row align="center" dense>
          <!-- 已拥有筛选 -->
          <v-col cols="auto">
            <v-switch
              v-model="localFilters.showOwnedOnly"
              color="primary"
              density="compact"
              hide-details
              label="仅显示已拥有"
              @update:model-value="emitUpdate"
            />
          </v-col>

          <v-divider class="mx-2" vertical />

          <!-- 基础属性筛选 -->
          <v-col cols="auto">
            <v-select
              v-model="localFilters.attributeId"
              clearable
              density="compact"
              hide-details
              item-title="name"
              item-value="id"
              :items="attributeItems"
              label="基础属性"
              style="min-width: 120px;"
              variant="outlined"
              @update:model-value="emitUpdate"
            />
          </v-col>

          <!-- 附加属性筛选 -->
          <v-col cols="auto">
            <v-select
              v-model="localFilters.secondaryId"
              clearable
              density="compact"
              hide-details
              item-title="name"
              item-value="id"
              :items="secondaryItems"
              label="附加属性"
              style="min-width: 140px;"
              variant="outlined"
              @update:model-value="emitUpdate"
            />
          </v-col>

          <!-- 技能属性筛选 -->
          <v-col cols="auto">
            <v-select
              v-model="localFilters.skillId"
              clearable
              density="compact"
              hide-details
              item-title="name"
              item-value="id"
              :items="skillItems"
              label="技能属性"
              style="min-width: 120px;"
              variant="outlined"
              @update:model-value="emitUpdate"
            />
          </v-col>

          <v-spacer />

          <!-- 搜索编码 -->
          <v-col cols="auto">
            <v-text-field
              v-model="localFilters.searchCode"
              clearable
              density="compact"
              hide-details
              label="搜索编码"
              prepend-inner-icon="mdi-magnify"
              style="width: 150px;"
              variant="outlined"
              @update:model-value="emitUpdate"
            />
          </v-col>

          <!-- 重置按钮 -->
          <v-col cols="auto">
            <v-btn
              icon
              size="small"
              title="重置筛选"
              variant="text"
              @click="resetFilters"
            >
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-col>
        </v-row>

        <!-- 活动筛选器标签 -->
        <div v-if="hasActiveFilters" class="mt-2">
          <v-chip
            v-if="localFilters.showOwnedOnly"
            closable
            size="x-small"
            @click:close="localFilters.showOwnedOnly = false; emitUpdate()"
          >
            仅已拥有
          </v-chip>
          <v-chip
            v-if="localFilters.attributeId"
            closable
            color="primary"
            size="x-small"
            @click:close="localFilters.attributeId = null; emitUpdate()"
          >
            {{ attributeNames[localFilters.attributeId] }}
          </v-chip>
          <v-chip
            v-if="localFilters.secondaryId"
            closable
            color="secondary"
            size="x-small"
            @click:close="localFilters.secondaryId = null; emitUpdate()"
          >
            {{ secondaryNames[localFilters.secondaryId] }}
          </v-chip>
          <v-chip
            v-if="localFilters.skillId"
            closable
            color="accent"
            size="x-small"
            @click:close="localFilters.skillId = null; emitUpdate()"
          >
            {{ skillNames[localFilters.skillId] }}
          </v-chip>
          <v-chip
            v-if="localFilters.searchCode"
            closable
            size="x-small"
            @click:close="localFilters.searchCode = ''; emitUpdate()"
          >
            搜索: {{ localFilters.searchCode }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

// ============================================================================
// 类型定义
// ============================================================================

interface Filters {
  showOwnedOnly: boolean
  attributeId: string | null
  secondaryId: string | null
  skillId: string | null
  searchCode: string
}

// ============================================================================
// Props
// ============================================================================

const props = defineProps<{
  filters: Filters
  attributeIds: string[]
  secondaryIds: string[]
  skillIds: string[]
  attributeNames: Record<string, string>
  secondaryNames: Record<string, string>
  skillNames: Record<string, string>
}>()

// ============================================================================
// Emits
// ============================================================================

const emit = defineEmits<{
  'update:filters': [filters: Filters]
}>()

// ============================================================================
// 状态
// ============================================================================

const localFilters = ref<Filters>({ ...props.filters })

// ============================================================================
// 计算属性
// ============================================================================

const attributeItems = computed(() => {
  return props.attributeIds.map(id => ({
    id,
    name: props.attributeNames[id] || id,
  }))
})

const secondaryItems = computed(() => {
  return props.secondaryIds.map(id => ({
    id,
    name: props.secondaryNames[id] || id,
  }))
})

const skillItems = computed(() => {
  return props.skillIds.map(id => ({
    id,
    name: props.skillNames[id] || id,
  }))
})

const hasActiveFilters = computed(() => {
  return (
    localFilters.value.showOwnedOnly ||
    localFilters.value.attributeId !== null ||
    localFilters.value.secondaryId !== null ||
    localFilters.value.skillId !== null ||
    localFilters.value.searchCode !== ''
  )
})

// ============================================================================
// 方法
// ============================================================================

function emitUpdate() {
  emit('update:filters', { ...localFilters.value })
}

function resetFilters() {
  localFilters.value = {
    showOwnedOnly: false,
    attributeId: null,
    secondaryId: null,
    skillId: null,
    searchCode: '',
  }
  emitUpdate()
}

// ============================================================================
// 监听器
// ============================================================================

watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = { ...newFilters }
  },
  { deep: true }
)
</script>

<style scoped>
.matrix-filters {
  width: 100%;
}
</style>
