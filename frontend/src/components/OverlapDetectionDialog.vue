<template>
  <!-- 自定义基质重合检测弹窗 -->
  <v-dialog v-model="overlapDialog" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="warning">mdi-alert-circle-outline</v-icon>
        自定义基质重合检测
      </v-card-title>
      <v-card-text>
        <v-alert class="mb-4" type="info" variant="tonal">
          以下自定义基质与内置武器词条重复，可选择移除或切换。
        </v-alert>
        <div
          v-for="(item, idx) in overlapItems"
          :key="idx"
          class="d-flex align-center mb-3 pa-3 border rounded flex-wrap"
          style="gap: 8px"
        >
          <v-tooltip location="top" open-delay="0">
            <template #activator="{ props: tooltipProps }">
              <div v-bind="tooltipProps" class="overlap-icon-wrapper" :class="{ 'weapon-not-owned': !isWeaponOwned(item.customWeaponId) }">
                <custom-stat-icon hide-name :name="item.customName" :skill-stat-id="customStats[item.customIndex]?.skill ?? null" small/>
              </div>
            </template>
            <span>{{ getOverlapTooltipText(item.customWeaponId) }}</span>
          </v-tooltip>
          <span class="font-weight-bold">{{ item.customName }}</span>
          <v-icon
            :color="getOverlapCompareResult(item) > 0 ? 'success' : getOverlapCompareResult(item) < 0 ? 'error' : 'grey'"
            size="small"
          >
            {{ getOverlapCompareResult(item) > 0 ? 'mdi-arrow-right-bold' : getOverlapCompareResult(item) < 0 ? 'mdi-arrow-left-bold' : 'mdi-arrow-left-right' }}
          </v-icon>
          <v-tooltip location="top" open-delay="0">
            <template #activator="{ props: tooltipProps }">
              <div v-bind="tooltipProps" class="overlap-icon-wrapper" :class="{ 'weapon-not-owned': !isWeaponOwned(item.matchedWeaponId) }">
                <item-icon class="weapon-icon-overlap" :item-id="item.matchedWeaponId" />
              </div>
            </template>
            <span>{{ getOverlapTooltipText(item.matchedWeaponId) }}</span>
          </v-tooltip>
          <span class="font-weight-bold">{{ item.matchedWeaponName }}</span>
          <v-spacer />
          <v-chip-group v-model="item.action" mandatory>
            <v-chip color="error" filter size="small" value="delete" variant="outlined">移除</v-chip>
            <v-chip color="primary" filter size="small" value="switch" variant="outlined">切换</v-chip>
            <v-chip filter size="small" value="ignore" variant="outlined">本次忽略</v-chip>
            <v-chip filter size="small" value="suppress" variant="outlined">不再提示</v-chip>
          </v-chip-group>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-btn color="secondary" variant="outlined" @click="autoSelectOverlap">一键选择</v-btn>
        <v-spacer />
        <v-btn @click="overlapDialog = false">取消</v-btn>
        <v-btn color="primary" @click="confirmOverlapActions">确认</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { useCustomStats } from '@/composables/useCustomStats'
import { useOverlapDetection } from '@/composables/useOverlapDetection'
import { useProfiles } from '@/composables/useProfiles'
import { useWeaponStats } from '@/composables/useWeaponStats'

const {
  overlapItems,
  overlapDialog,
  getOverlapCompareResult,
  autoSelectOverlap,
  getOverlapTooltipText: getOverlapTooltipTextBase,
  confirmOverlapActions: confirmOverlapActionsBase,
} = useOverlapDetection()
const { customStats, fetchCustomStats } = useCustomStats()
const { matrixEntryByWeaponId, isWeaponOwned } = useWeaponStats()
const { treasureMatrix } = useProfiles()

/** 获取重合检测的工具提示文本 */
function getOverlapTooltipText(weaponId: string): string {
  return getOverlapTooltipTextBase(weaponId, {
    matrixEntryByWeaponId: matrixEntryByWeaponId.value,
    customStats: customStats.value,
  })
}

/** 确认重合操作 */
async function confirmOverlapActions() {
  try {
    await confirmOverlapActionsBase({
      customStats: customStats.value,
      treasureMatrix: treasureMatrix.value,
      matrixEntryByWeaponId: matrixEntryByWeaponId.value,
    })
    overlapDialog.value = false
    await fetchCustomStats()
  } catch (error) {
    console.error('确认重合操作失败:', error)
    // TODO: 显示 snackbar 错误提示
  }
}
</script>

<style scoped lang="scss">
.overlap-icon-wrapper {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;

  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }
}

.weapon-icon-overlap {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}
</style>
