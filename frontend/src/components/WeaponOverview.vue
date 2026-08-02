<template>
  <v-expansion-panel value="武器总览">
    <v-expansion-panel-title>
      <v-icon class="mr-2">mdi-sword-cross</v-icon>
      武器总览
      <v-chip class="ml-2" color="success" size="small" variant="flat">
        {{ ownedCount }} / {{ totalCount }}
      </v-chip>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-alert border="start" class="mb-4" type="info" variant="tonal">
        左键点击武器图标查看基质属性，右键点击切换是否拥有该武器的基质。已满级（6/6/3）的武器会显示彩虹边框。鼠标悬停在有相同属性的武器上会显示粒子连线。
      </v-alert>

      <!-- 星级过滤开关 -->
      <div class="d-flex align-center gap-2 mb-4">
        <span class="text-body-2 text-medium-emphasis">显示星级：</span>
        <v-chip-group v-model="selectedRarities" column multiple>
          <v-chip
            color="primary"
            filter
            size="small"
            value="3"
            variant="outlined"
          >
            3★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="4"
            variant="outlined"
          >
            4★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="5"
            variant="outlined"
          >
            5★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="6"
            variant="outlined"
          >
            6★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="custom"
            variant="outlined"
          >
            自定义
          </v-chip>
        </v-chip-group>
      </div>

      <!-- 自定义基质重合检测按钮 + 可切换提示模式 + 基质图标显示模式 -->
      <div class="d-flex align-center ga-2 mb-4">
        <v-btn
          color="warning"
          prepend-icon="mdi-swap-horizontal"
          size="small"
          variant="tonal"
          @click="checkCustomOverlap"
        >
          检查自定义基质重合
        </v-btn>
        <v-btn
          :prepend-icon="matrixBadgeModeIcons[matrixBadgeDisplayMode]"
          size="small"
          variant="tonal"
          @click="toggleMatrixBadgeDisplayMode"
        >
          {{ matrixBadgeModeLabels[matrixBadgeDisplayMode] }}
        </v-btn>
        <v-btn
          :prepend-icon="switchModeIcons[switchDisplayMode]"
          size="small"
          variant="tonal"
          @click="toggleSwitchDisplayMode"
        >
          {{ switchModeLabels[switchDisplayMode] }}
        </v-btn>
      </div>

      <!-- 武器总览容器（包含连线层） -->
      <div ref="containerRef" class="weapon-overview-container">
        <!-- 连线层 -->
        <div class="connection-lines-layer">
          <div
            v-for="(line, index) in connectionLines"
            :key="index"
            class="connection-line"
            :style="line.style"
          />
        </div>

        <!-- 自定义基质区段 -->
        <template v-if="showCustomSection">
          <div class="d-flex align-center mb-1 mt-3">
            <img alt="基质底板" class="essence-icon-small me-2" :src="essenceBgSrc" />
            <h4>自定义基质</h4>
          </div>
          <div class="weapon-overview-grid">
            <!-- [+] 新建按钮 -->
            <div
              class="weapon-overview-item"
              @click="showNewCustomDialog"
            >
              <div class="weapon-add-button">
                <v-icon color="grey" size="28">mdi-plus</v-icon>
              </div>
            </div>
            <div
              v-for="entry in customMatrixEntries"
              :key="entry.syntheticId"
              class="weapon-overview-item"
              :data-weapon-id="entry.syntheticId"
              @click="showWeaponDetail(entry.syntheticId)"
              @contextmenu.prevent="toggleWeaponOwnership(entry.syntheticId)"
              @mouseenter="handleWeaponMouseEnter(entry.syntheticId)"
              @mouseleave="handleWeaponMouseLeave"
            >
              <!-- 武器悬浮面板：显示自定义基质的三条属性 -->
              <v-tooltip location="top" open-delay="0">
                <template #activator="{ props }">
                  <div v-bind="props" class="h-100">
                    <div
                      class="weapon-icon-wrapper"
                      :class="{
                        'weapon-not-owned': !isWeaponOwned(entry.syntheticId),
                        'weapon-maxed': isWeaponMaxed(entry.syntheticId),
                      }"
                    >
                      <custom-stat-icon :name="entry.displayName" :skill-stat-id="entry.skillStatId" />

                      <!-- 满级的彩虹边框 -->
                      <div v-if="isWeaponMaxed(entry.syntheticId)" class="rainbow-border" />
                    </div>
                  </div>
                </template>
                <span>{{ getWeaponStatsText(entry.syntheticId) }}</span>
              </v-tooltip>
            </div>
          </div>
        </template>

        <template v-for="wType in filteredWeaponTypes" :key="wType.id">
          <div class="d-flex align-center mb-1 mt-3">
            <img
              :alt="wType.name"
              class="group-icon me-2"
              :src="wType.iconUrl"
            />
            <h4>{{ wType.name }}</h4>
          </div>
          <div class="weapon-overview-grid">
            <div
              v-for="weaponId in wType.weaponIds"
              :key="weaponId"
              class="weapon-overview-item"
              :data-weapon-id="weaponId"
              @click="showWeaponDetail(weaponId)"
              @contextmenu.prevent="toggleWeaponOwnership(weaponId)"
              @mouseenter="handleWeaponMouseEnter(weaponId)"
              @mouseleave="handleWeaponMouseLeave"
            >
              <!-- 武器悬浮面板：显示武器的三条基质属性 -->
              <v-tooltip location="top" open-delay="0">
                <template #activator="{ props }">
                  <div v-bind="props" class="h-100">
                    <div
                      class="weapon-icon-wrapper"
                      :class="{
                        'weapon-not-owned': !isWeaponOwned(weaponId),
                        'weapon-maxed': isWeaponMaxed(weaponId),
                        'switch-target-maxed': isSwitchable(weaponId) && isSwitchTargetMaxed(weaponId) && !isWeaponMaxed(weaponId),
                      }"
                    >
                      <item-icon :item-id="weaponId" show-item-name />

                      <!-- 左上角：缩小版圆形基质图标（底板+技能属性叠加） -->
                      <div
                        v-if="matrixBadgeDisplayMode !== 'off'"
                        class="weapon-matrix-badge"
                        :class="{
                          'weapon-matrix-badge--medium': matrixBadgeDisplayMode === 'medium',
                        }"
                      >
                        <img alt="基质底板" class="weapon-matrix-badge-bg" :src="essenceBgSrc" />
                        <img v-if="getWeaponSkillIcon(weaponId)" alt="技能" class="weapon-matrix-badge-skill" :src="getWeaponSkillIcon(weaponId)!" />
                      </div>

                      <!-- 满级的彩虹边框 -->
                      <div v-if="isWeaponMaxed(weaponId)" class="rainbow-border" />
                    </div>
                  </div>
                </template>
                <span>{{ getWeaponStatsText(weaponId) }}</span>
              </v-tooltip>

              <!-- 可切换标记：根据模式显示标签/圆点/关闭 -->
              <v-chip
                v-if="switchDisplayMode === 'chip' && isSwitchable(weaponId) && !isWeaponMaxed(weaponId)"
                class="switchable-badge"
                color="warning"
                size="x-small"
                variant="flat"
              >
                可切换
              </v-chip>
              <div
                v-else-if="switchDisplayMode === 'dot' && isSwitchable(weaponId) && !isWeaponMaxed(weaponId)"
                class="switch-dot"
              />
            </div>
          </div>
        </template>
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>

  <!-- 武器详情弹窗 -->
  <v-dialog v-model="detailDialog" max-width="680">
    <v-card v-if="detailWeaponId">
      <v-card-item>
        <template #prepend>
          <custom-stat-icon v-if="isCustomEntry(detailWeaponId) || isNewCustom" class="weapon-icon-detail" hide-name :name="customEntryName || '新基质'" :skill-stat-id="customEditSkill" />
          <item-icon v-else class="weapon-icon-detail" :item-id="detailWeaponId" />
        </template>
        <v-card-title>
          <v-text-field
            v-if="isCustomEntry(detailWeaponId) || isNewCustom"
            v-model="customEntryName"
            density="compact"
            hide-details
            placeholder="自定义基质名称"
            variant="underlined"
          />
          <template v-else>
            {{ weaponsMap.get(detailWeaponId)?.name || detailWeaponId }}
          </template>
        </v-card-title>
        <template #append>
          <v-btn icon="mdi-close" variant="text" @click="detailDialog = false" />
        </template>
      </v-card-item>
      <v-divider />
      <v-card-text>
        <!-- 基质属性 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-2">基质属性</div>
          <v-row dense>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="isCustomEntry(detailWeaponId) || isNewCustom"
                density="compact"
                :disabled="!(isCustomEntry(detailWeaponId) || isNewCustom)"
                hide-details
                :items="allAttributeStats.map(id => ({ title: getGemTagName(id), value: id }))"
                label="基础属性"
                :model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditAttribute : weaponsMap.get(detailWeaponId)?.attributeStatId ?? null"
                variant="outlined"
                @update:model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditAttribute = $event : undefined"
              />
            </v-col>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="isCustomEntry(detailWeaponId) || isNewCustom"
                density="compact"
                :disabled="!(isCustomEntry(detailWeaponId) || isNewCustom)"
                hide-details
                :items="allSecondaryStats.map(id => ({ title: getGemTagName(id), value: id }))"
                label="附加属性"
                :model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditSecondary : weaponsMap.get(detailWeaponId)?.secondaryStatId ?? null"
                variant="outlined"
                @update:model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditSecondary = $event : undefined"
              />
            </v-col>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="isCustomEntry(detailWeaponId) || isNewCustom"
                density="compact"
                :disabled="!(isCustomEntry(detailWeaponId) || isNewCustom)"
                hide-details
                :items="allSkillStats.map(id => ({ title: getGemTagName(id), value: id }))"
                label="技能属性"
                :model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditSkill : weaponsMap.get(detailWeaponId)?.skillStatId ?? null"
                variant="outlined"
                @update:model-value="isCustomEntry(detailWeaponId) || isNewCustom ? customEditSkill = $event : undefined"
              />
            </v-col>
          </v-row>
        </div>

        <!-- 基质等级 -->
        <div class="mb-4 detail-level-outer">
          <div class="text-subtitle-2 mb-2">当前基质等级</div>
          <div class="detail-level-wrapper">
            <div class="detail-level-section">
              <div class="detail-attr-control detail-attr-control--primary">
                <span class="detail-attr-label">基础属性</span>
                <div class="detail-attr-pips">
                  <span
                    v-for="level in affixLevelItems"
                    :key="`d-a1-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= detailAffix1,
                      'detail-pip--max': detailAffix1 === 6,
                    }"
                    @click="detailAffix1 = level"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': detailAffix1 === 6 }">
                  +{{ detailAffix1 }} / 6
                </span>
              </div>

              <div class="detail-attr-control detail-attr-control--teal">
                <span class="detail-attr-label">附加属性</span>
                <div class="detail-attr-pips">
                  <span
                    v-for="level in affixLevelItems"
                    :key="`d-a2-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= detailAffix2,
                      'detail-pip--max': detailAffix2 === 6,
                    }"
                    @click="detailAffix2 = level"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': detailAffix2 === 6 }">
                  +{{ detailAffix2 }} / 6
                </span>
              </div>

              <div class="detail-attr-control detail-attr-control--indigo">
                <span class="detail-attr-label">技能属性</span>
                <div class="detail-attr-pips detail-attr-pips--skill">
                  <span
                    v-for="level in skillLevelItems"
                    :key="`d-a3-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= detailAffix3,
                      'detail-pip--max': detailAffix3 === 3,
                    }"
                    @click="detailAffix3 = level"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': detailAffix3 === 3 }">
                  +{{ detailAffix3 }} / 3
                </span>
              </div>
            </div>

            <!-- 未拥有斜向胶带遮罩（贯穿三个属性，可点击切换拥有） -->
            <transition name="tape-peel">
              <div
                v-if="!isDetailOwned"
                class="not-owned-tape-detail"
                @click="toggleDetailOwnership"
              >
                <span class="not-owned-tape-detail-text">» 未拥有 » NOT OWNED » 点击切换为拥有 » CLICK TO TOGGLE » </span>
              </div>
            </transition>
          </div>

          <!-- 未拥有遮罩：覆盖等级区域，阻止交互 -->
          <div v-if="!isDetailOwned" class="not-owned-block-overlay" @click="toggleDetailOwnership" />

          <!-- 拥有状态切换 -->
          <div class="mt-2">
            <v-chip
              :color="isDetailOwned ? 'success' : 'grey'"
              :prepend-icon="isDetailOwned ? 'mdi-check-circle' : 'mdi-close-circle'"
              size="small"
              variant="tonal"
              @click="toggleDetailOwnership"
            >
              {{ isDetailOwned ? '已拥有 · 点击可切换为 未拥有' : '未拥有 · 点击可切换为 已拥有' }}
            </v-chip>
          </div>
        </div>

        <!-- 优先级设置 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-1">基质匹配优先级</div>
          <div class="d-flex flex-wrap align-center ga-2 mb-2">
            <v-chip
              v-for="p in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
              :key="p"
              :color="detailPriority === p ? 'primary' : undefined"
              size="small"
              :variant="detailPriority === p ? 'flat' : 'outlined'"
              @click="detailPriority = p"
            >
              {{ p }}
            </v-chip>
          </div>
          <div class="text-caption text-medium-emphasis" style="line-height: 1.6">
            当扫描到一个无暇基质同时匹配多把武器时，系统会按优先级将该基质分配给优先级最高的武器。<br />
            默认使用武器稀有度作为优先级（6★=6, 5★=5, 4★=4, 3★=3）。<br />
            手动设置 1-9 可覆盖默认值，数值越大越优先。<br />
            已满级（6/6/3）的武器会被自动跳过。
          </div>
        </div>

        <!-- 同类武器（仅非自定义且非新建时显示） -->
        <div v-if="!isCustomEntry(detailWeaponId) && !isNewCustom && getSameStatWeapons(detailWeaponId).length > 0">
          <div class="text-subtitle-2 mb-2">同类属性武器</div>
          <div class="d-flex flex-column ga-2">
            <v-card
              v-for="sameId in getSameStatWeapons(detailWeaponId)"
              :key="sameId"
              class="pa-2"
              variant="outlined"
            >
              <div class="d-flex align-center justify-space-between">
                <div class="d-flex align-center ga-2">
                  <item-icon class="weapon-icon-same" :item-id="sameId" />
                  <div>
                    <div class="font-weight-bold text-body-2">
                      {{ weaponsMap.get(sameId)?.name || sameId }}
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      {{ getMatrixLevelText(sameId) }}
                      <span class="ml-1">优先级: {{ getWeaponPriority(sameId) }}</span>
                    </div>
                  </div>
                </div>
                <v-btn
                  color="primary"
                  size="small"
                  variant="tonal"
                  @click="swapMatrix(detailWeaponId!, sameId)"
                >
                  交换
                </v-btn>
              </div>
            </v-card>
          </div>
        </div>
        <div v-else-if="!isCustomEntry(detailWeaponId) && !isNewCustom" class="text-medium-emphasis text-caption">
          没有其他武器与此武器共享相同属性组合。
        </div>
      </v-card-text>

      <!-- 操作按钮 -->
      <v-divider />
      <v-card-actions>
        <!-- 自定义基质（新建+编辑）：保存 + 删除 -->
        <template v-if="isCustomEntry(detailWeaponId) || isNewCustom">
          <v-btn
            v-if="!isNewCustom"
            color="error"
            prepend-icon="mdi-delete"
            variant="text"
            @click="promptDeleteCustomEntry"
            @mousedown="pendingCustomDelete = true"
          >
            删除此自定义基质·无法恢复
          </v-btn>
          <v-spacer />
          <v-btn
            color="primary"
            prepend-icon="mdi-content-save"
            variant="flat"
            @click="saveCustomEntry"
          >
            保存
          </v-btn>
        </template>
        <!-- 非自定义基质：清空 -->
        <template v-else>
          <v-btn
            v-if="isWeaponOwned(detailWeaponId)"
            color="error"
            prepend-icon="mdi-delete-outline"
            variant="text"
            @click="removeNonCustomEntry(detailWeaponId!)"
          >
            清空此基质的保存数据
          </v-btn>
          <v-spacer />
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 自定义基质重合检测弹窗 -->
  <v-dialog v-model="overlapDialog" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="warning">mdi-alert-circle-outline</v-icon>
        自定义基质重合检测
      </v-card-title>
      <v-card-text>
        <v-alert class="mb-4" type="info" variant="tonal">
          以下自定义基质与内置武器的三个词条完全相同，可选择切换为内置武器。
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
            <v-chip color="error" filter size="small" value="delete" variant="outlined">删除自定义基质</v-chip>
            <v-chip filter size="small" value="ignore" variant="outlined">本次忽略</v-chip>
            <v-chip filter size="small" value="suppress" variant="outlined">不再提示</v-chip>
            <v-chip color="primary" filter size="small" value="switch" variant="outlined">切换</v-chip>
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

  <!-- 删除自定义基质确认弹窗 -->
  <v-dialog v-model="deleteCustomConfirm" max-width="460">
    <v-card>
      <v-card-title class="text-error">删除自定义基质</v-card-title>
      <v-card-text>
        确定要删除自定义基质「{{ deleteCustomName }}」吗？将从设置中移除该基质定义，并从当前账号的基质数据中移除对应条目，此操作不可撤销。
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancelDeleteCustomEntry">取消</v-btn>
        <v-btn color="error" @click="confirmDeleteCustomEntry">删除</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useRarityFilters } from '@/composables/useRarityFilters'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'

const { weaponTypes, weaponsMap, essencesMap, matrixIcons } = useStaticData()
const {
  activeProfile,
  treasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  updateTreasureMatrix,
  updateSwitchDisplayMode,
  updateMatrixBadgeDisplayMode,
  updateWeaponPriority,
} = useProfiles()
const { selectedRarities } = useRarityFilters()

// 可切换提示显示模式：'chip'=大号提示(默认), 'dot'=小橙点, 'off'=关闭
type SwitchDisplayMode = 'chip' | 'dot' | 'off'
const switchDisplayMode = ref<SwitchDisplayMode>((activeProfile.value.switch_display_mode ?? 'chip') as SwitchDisplayMode)
const switchModeLabels: Record<SwitchDisplayMode, string> = {
  chip: '切换提示：标签',
  dot: '切换提示：圆点',
  off: '切换提示：关闭',
}
const switchModeIcons: Record<SwitchDisplayMode, string> = {
  chip: 'mdi-tag-outline',
  dot: 'mdi-circle-small',
  off: 'mdi-eye-off-outline',
}
function toggleSwitchDisplayMode() {
  const next: SwitchDisplayMode = switchDisplayMode.value === 'chip' ? 'dot' : switchDisplayMode.value === 'dot' ? 'off' : 'chip'
  switchDisplayMode.value = next
  updateSwitchDisplayMode(next)
}

// 切换账号时同步显示模式
watch(() => activeProfile.value.switch_display_mode, (mode) => {
  if (mode && mode !== switchDisplayMode.value) {
    switchDisplayMode.value = mode
  }
})

// 基质图标显示模式：'small'=小号(默认), 'medium'=中号(2倍), 'off'=关闭
type MatrixBadgeDisplayMode = 'small' | 'medium' | 'off'
const matrixBadgeDisplayMode = ref<MatrixBadgeDisplayMode>((activeProfile.value.matrix_badge_display_mode ?? 'small') as MatrixBadgeDisplayMode)
const matrixBadgeModeLabels: Record<MatrixBadgeDisplayMode, string> = {
  small: '基质图标：小号',
  medium: '基质图标：中号',
  off: '基质图标：关闭',
}
const matrixBadgeModeIcons: Record<MatrixBadgeDisplayMode, string> = {
  small: 'mdi-circle-outline',
  medium: 'mdi-circle-double',
  off: 'mdi-eye-off-outline',
}
function toggleMatrixBadgeDisplayMode() {
  const next: MatrixBadgeDisplayMode = matrixBadgeDisplayMode.value === 'small' ? 'medium' : matrixBadgeDisplayMode.value === 'medium' ? 'off' : 'small'
  matrixBadgeDisplayMode.value = next
  updateMatrixBadgeDisplayMode(next)
}

// 切换账号时同步基质图标显示模式
watch(() => activeProfile.value.matrix_badge_display_mode, (mode) => {
  if (mode && mode !== matrixBadgeDisplayMode.value) {
    matrixBadgeDisplayMode.value = mode
  }
})

// 底板图片路径
const essenceBgSrc = computed(() => matrixIcons.value.essenceBg)

// --- 武器卡片辅助函数 ---

/** 获取武器的技能属性图标 URL */
function getWeaponSkillIcon(weaponId: string): string | null {
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    if (!stat?.skill) return null
    return matrixIcons.value.skills[stat.skill] || null
  }
  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon?.skillStatId) return null
  return matrixIcons.value.skills[weapon.skillStatId] || null
}

// --- 属性选项列表 ---
const allAttributeStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'ATTRIBUTE')
    .map((e) => e.id),
)
const allSecondaryStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'SECONDARY')
    .map((e) => e.id),
)
const allSkillStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'SKILL')
    .map((e) => e.id),
)

// --- 等级选项 ---
const affixLevelItems = [1, 2, 3, 4, 5, 6]
const skillLevelItems = [1, 2, 3]

// 武器详情弹窗
const detailDialog = ref(false)
const detailWeaponId = ref<string | null>(null)

// --- 武器连线系统 ---

/** 容器引用 */
const containerRef = ref<HTMLElement | null>(null)

/** 当前悬停的武器 ID */
const hoveredWeaponId = ref<string | null>(null)

/** 连线数据 */
interface ConnectionLine {
  style: {
    left: string
    top: string
    width: string
    transform: string
    opacity: number
  }
}

const connectionLines = ref<ConnectionLine[]>([])

/** 获取武器图标元素位置 */
function getWeaponElementPosition(weaponId: string): { x: number; y: number } | null {
  const container = containerRef.value
  if (!container) return null

  const element = container.querySelector(`[data-weapon-id="${weaponId}"]`)
  if (!element) return null

  const containerRect = container.getBoundingClientRect()
  const elementRect = element.getBoundingClientRect()

  return {
    x: elementRect.left - containerRect.left + elementRect.width / 2,
    y: elementRect.top - containerRect.top + elementRect.height / 2,
  }
}

/** 计算两点之间的距离和角度 */
function calculateLine(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): { length: number; angle: number } {
  const dx = endX - startX
  const dy = endY - startY
  const length = Math.hypot(dx, dy)
  const angle = Math.atan2(dy, dx) * (180 / Math.PI)
  return { length, angle }
}

/** 更新连线 */
function updateConnectionLines() {
  if (!hoveredWeaponId.value) {
    connectionLines.value = []
    return
  }

  const startPos = getWeaponElementPosition(hoveredWeaponId.value)
  if (!startPos) {
    connectionLines.value = []
    return
  }

  const sameWeapons = getSameStatWeapons(hoveredWeaponId.value)
  const newLines: ConnectionLine[] = []

  for (const targetId of sameWeapons) {
    const endPos = getWeaponElementPosition(targetId)
    if (!endPos) continue

    const { length, angle } = calculateLine(
      startPos.x,
      startPos.y,
      endPos.x,
      endPos.y,
    )

    newLines.push({
      style: {
        left: `${startPos.x}px`,
        top: `${startPos.y}px`,
        width: `${length}px`,
        transform: `rotate(${angle}deg)`,
        opacity: 1,
      },
    })
  }

  connectionLines.value = newLines
}

/** 鼠标进入武器 */
function handleWeaponMouseEnter(weaponId: string) {
  hoveredWeaponId.value = weaponId
  updateConnectionLines()
}

/** 鼠标离开武器 */
function handleWeaponMouseLeave() {
  hoveredWeaponId.value = null
  connectionLines.value = []
}

// 监听窗口大小变化，更新连线位置
onMounted(() => {
  window.addEventListener('resize', updateConnectionLines)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateConnectionLines)
  connectionLines.value = []
})

// --- 自定义基质相关 ---

/** 自定义宝藏基质属性配置列表 */
const customStats = ref<Array<{ name: string; attribute: string | null; secondary: string | null; skill: string | null; no_prompt_switch?: boolean }>>([])

// --- 详情弹窗编辑状态 ---

/** 新建模式标识 */
const isNewCustom = computed(() => detailWeaponId.value === '__new_custom__')

/** 自定义基质编辑中的属性 */
const customEditAttribute = ref<string | null>(null)
const customEditSecondary = ref<string | null>(null)
const customEditSkill = ref<string | null>(null)

/** 等级编辑状态 */
const detailAffix1 = ref(1)
const detailAffix2 = ref(1)
const detailAffix3 = ref(1)

/** 优先级编辑状态 */
const detailPriority = ref(6)

/** 新建模式下的拥有状态（用户手动切换） */
const detailOwnedOverride = ref(false)

/** 当前弹窗中的条目是否已拥有 */
const isDetailOwned = computed(() => {
  const weaponId = detailWeaponId.value
  if (!weaponId) return false
  if (weaponId === '__new_custom__') return detailOwnedOverride.value
  return isWeaponOwned(weaponId)
})

/** 切换当前弹窗条目的拥有状态 */
async function toggleDetailOwnership() {
  const weaponId = detailWeaponId.value
  if (!weaponId) return
  if (weaponId === '__new_custom__') {
    detailOwnedOverride.value = !detailOwnedOverride.value
  } else {
    await toggleWeaponOwnership(weaponId)
  }
}

// --- 自定义基质与内置武器重合检测 ---

interface OverlapItem {
  customIndex: number
  customName: string
  customWeaponId: string
  matchedWeaponId: string
  matchedWeaponName: string
  action: 'ignore' | 'suppress' | 'switch' | 'delete'
}

const overlapItems = ref<OverlapItem[]>([])
const overlapDialog = ref(false)
/** 重合检测的等级比较结果（按 overlapItems 索引缓存） */
const overlapCompareResults = ref<Map<number, number>>(new Map())

/** 从后端获取配置中的自定义宝藏基质属性列表 */
async function fetchCustomStats() {
  try {
    const res = await fetch('/api/config')
    const config = await res.json()
    customStats.value = config.treasure_essence_stats || []
  } catch (error) {
    console.error('获取自定义宝藏基质配置失败:', error)
  }
}

/** 判断是否为自定义基质条目（weapon_id 以 custom_stat_ 开头） */
function isCustomEntry(weaponId: string | null): boolean {
  return weaponId?.startsWith('custom_stat_') ?? false
}

/** 自定义基质条目列表，用于武器总览展示 */
const customMatrixEntries = computed(() => {
  return customStats.value
    .map((stat, index) => ({
      syntheticId: `custom_stat_${index}`,
      displayName: stat.name || `自定义基质 ${index + 1}`,
      index,
      skillStatId: stat.skill,
    }))
})

/** 是否显示自定义基质区段（当 6★ 筛选激活时显示） */
const showCustomSection = computed(() => selectedRarities.value.includes('custom'))

/** 自定义条目编辑中的名称 */
const customEntryName = ref('')

// --- 删除自定义基质 ---
const deleteCustomConfirm = ref(false)
const deleteCustomIndex = ref<number | null>(null)
const deleteCustomName = ref('')
// 标记「正在发起删除」：删除按钮按下（mousedown）时置位，用于让名称输入框的
// @blur 保存跳过本次写入，避免与删除流程交错写后端。
const pendingCustomDelete = ref(false)

// 弹窗打开时，加载编辑状态
watch([detailDialog, detailWeaponId], () => {
  // 弹窗关闭时复位删除标记，避免 mousedown 后放弃点击导致标记卡住
  if (!detailDialog.value) {
    pendingCustomDelete.value = false
    return
  }

  if (detailDialog.value) {
    const weaponId = detailWeaponId.value

    if (weaponId === '__new_custom__') {
      // 新建模式：重置所有字段
      customEntryName.value = ''
      customEditAttribute.value = null
      customEditSecondary.value = null
      customEditSkill.value = null
      detailAffix1.value = 1
      detailAffix2.value = 1
      detailAffix3.value = 1
      detailPriority.value = 6
      detailOwnedOverride.value = false
    } else if (isCustomEntry(weaponId)) {
      // 编辑自定义条目
      const index = Number.parseInt(weaponId!.replace('custom_stat_', ''), 10)
      const stat = customStats.value[index]
      customEntryName.value = stat?.name || ''
      customEditAttribute.value = stat?.attribute ?? null
      customEditSecondary.value = stat?.secondary ?? null
      customEditSkill.value = stat?.skill ?? null
      // 从 profile 中读取等级
      const entry = matrixEntryByWeaponId.value.get(weaponId!)
      detailAffix1.value = entry?.affix1_level ?? 1
      detailAffix2.value = entry?.affix2_level ?? 1
      detailAffix3.value = entry?.affix3_level ?? 1
      detailPriority.value = getWeaponPriority(weaponId!)
    } else {
      // 非自定义条目：从 profile 中读取等级
      const entry = matrixEntryByWeaponId.value.get(weaponId!)
      detailAffix1.value = entry?.affix1_level ?? 1
      detailAffix2.value = entry?.affix2_level ?? 1
      detailAffix3.value = entry?.affix3_level ?? 1
      detailPriority.value = getWeaponPriority(weaponId!)
    }
  }
})

// 确认弹窗以任意方式关闭（取消/遮罩/ESC）时复位删除标记，避免误跳过后续名称保存
watch(deleteCustomConfirm, (open) => {
  if (!open) pendingCustomDelete.value = false
})

/** 打开新建自定义基质弹窗 */
function showNewCustomDialog() {
  detailWeaponId.value = '__new_custom__'
  detailDialog.value = true
}

/** 保存自定义基质（新建或编辑） */
async function saveCustomEntry() {
  const weaponId = detailWeaponId.value
  if (!weaponId) return

  if (weaponId === '__new_custom__') {
    // 新建模式：先写入 config
    customStats.value.push({
      name: customEntryName.value || `自定义基质 ${customStats.value.length + 1}`,
      attribute: customEditAttribute.value,
      secondary: customEditSecondary.value,
      skill: customEditSkill.value,
    })
    await postCustomStatsUpdate()

    // 只有标记为"已拥有"时才写入 profile
    if (isDetailOwned.value) {
      const newIndex = customStats.value.length - 1
      const syntheticId = `custom_stat_${newIndex}`
      await addTreasureMatrixEntry({
        weapon_id: syntheticId,
        weapon_name: customEntryName.value || `自定义基质 ${newIndex + 1}`,
        affix1_level: detailAffix1.value,
        affix2_level: detailAffix2.value,
        affix3_level: detailAffix3.value,
        priority: detailPriority.value,
        include_in_calculation: true,
      })
    }
  } else if (isCustomEntry(weaponId)) {
    // 编辑模式：更新 config 和 profile
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    if (customStats.value[index]) {
      customStats.value[index].name = customEntryName.value
      customStats.value[index].attribute = customEditAttribute.value
      customStats.value[index].secondary = customEditSecondary.value
      customStats.value[index].skill = customEditSkill.value
      await postCustomStatsUpdate()
    }

    // 更新 profile 中的等级和优先级
    const entry = matrixEntryByWeaponId.value.get(weaponId)
    if (entry) {
      entry.weapon_name = customEntryName.value
      entry.affix1_level = detailAffix1.value
      entry.affix2_level = detailAffix2.value
      entry.affix3_level = detailAffix3.value
      entry.priority = detailPriority.value
      await updateTreasureMatrix([...treasureMatrix.value])
      await updateWeaponPriority(weaponId, detailPriority.value)
    }
  }

  detailDialog.value = false
  await fetchCustomStats()
}

/** 非自定义基质：从基质配置中移除 */
async function removeNonCustomEntry(weaponId: string) {
  await removeTreasureMatrixEntry(weaponId)
  detailDialog.value = false
}

/** 非自定义基质：等级/优先级变化时自动保存（防抖） */
let detailSaveTimer: ReturnType<typeof setTimeout> | null = null
watch([detailAffix1, detailAffix2, detailAffix3, detailPriority], async () => {
  const weaponId = detailWeaponId.value
  // 仅对已存在的非自定义条目自动保存
  if (!weaponId || weaponId === '__new_custom__' || isCustomEntry(weaponId)) return
  if (!isWeaponOwned(weaponId)) return

  if (detailSaveTimer) clearTimeout(detailSaveTimer)
  detailSaveTimer = setTimeout(async () => {
    const entry = matrixEntryByWeaponId.value.get(weaponId)
    if (entry) {
      entry.affix1_level = detailAffix1.value
      entry.affix2_level = detailAffix2.value
      entry.affix3_level = detailAffix3.value
      entry.priority = detailPriority.value
      await updateTreasureMatrix([...treasureMatrix.value])
      await updateWeaponPriority(weaponId, detailPriority.value)
    }
    detailSaveTimer = null
  }, 400)
})

/** 打开删除自定义基质的二次确认弹窗 */
function promptDeleteCustomEntry() {
  if (!isCustomEntry(detailWeaponId.value)) return
  const index = Number.parseInt(detailWeaponId.value!.replace('custom_stat_', ''), 10)
  if (Number.isNaN(index)) return
  deleteCustomIndex.value = index
  deleteCustomName.value = customStats.value[index]?.name || `自定义基质 ${index + 1}`
  deleteCustomConfirm.value = true
}

/** 取消删除 */
function cancelDeleteCustomEntry() {
  deleteCustomConfirm.value = false
  pendingCustomDelete.value = false
}

/**
 * 确认删除自定义基质：
 * 1. 基于未修改的 treasureMatrix 计算新矩阵（删除目标条目 + 重索引后续自定义条目）
 * 2. 从 config 的自定义列表移除该项
 * 3. 先写 profile（后端据此重建 weapon_priorities），再回写 config，最后回读
 */
async function confirmDeleteCustomEntry() {
  const index = deleteCustomIndex.value
  if (index === null) {
    cancelDeleteCustomEntry()
    return
  }
  const targetId = `custom_stat_${index}`

  // 1) 删除目标条目，并将所有索引 > index 的自定义条目前移一位
  const newMatrix = treasureMatrix.value
    .filter((e) => e.weapon_id !== targetId)
    .map((e) => {
      if (e.weapon_id.startsWith('custom_stat_')) {
        const cur = Number.parseInt(e.weapon_id.replace('custom_stat_', ''), 10)
        if (cur > index) return { ...e, weapon_id: `custom_stat_${cur - 1}` }
      }
      return e
    })

  // 2) 从 config 的自定义基质列表中移除该项
  customStats.value.splice(index, 1)

  // 3) 持久化：先 profile，再 config，最后回读配置
  await updateTreasureMatrix(newMatrix)
  await postCustomStatsUpdate()
  await fetchCustomStats()

  // 4) 关闭弹窗并清理引用（重索引后旧 syntheticId 已指向不同条目，必须清空）
  deleteCustomConfirm.value = false
  pendingCustomDelete.value = false
  detailDialog.value = false
  detailWeaponId.value = null
  deleteCustomIndex.value = null
}

/** 将自定义宝藏基质配置保存到后端 */
async function postCustomStatsUpdate() {
  try {
    const res = await fetch('/api/config')
    const currentConfig = await res.json()
    currentConfig.treasure_essence_stats = customStats.value
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig),
    })
  } catch (error) {
    console.error('保存自定义宝藏基质配置失败:', error)
  }
}

/** 获取重合检测中某个武器 ID 的属性词条文本（含等级） */
function getOverlapTooltipText(weaponId: string): string {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  const levels: [number, number, number] = [
    entry?.affix1_level ?? 0,
    entry?.affix2_level ?? 0,
    entry?.affix3_level ?? 0,
  ]

  let statIds: (string | null)[] = []
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    statIds = [stat?.attribute ?? null, stat?.secondary ?? null, stat?.skill ?? null]
  } else {
    const weapon = weaponsMap.value.get(weaponId)
    statIds = [weapon?.attributeStatId ?? null, weapon?.secondaryStatId ?? null, weapon?.skillStatId ?? null]
  }

  const parts: string[] = []
  for (let i = 0; i < 3; i++) {
    const sid = statIds[i]
    if (sid) {
      parts.push(`${getGemTagName(sid)} Lv.${levels[i]}`)
    }
  }
  return parts.join('、') || '无属性'
}

/**
 * 解析武器 ID 对应的三个槽位词条类型
 * 返回 ["ATTRIBUTE", "SECONDARY", "SKILL"] 或对应的 null
 */
function resolveStatTypes(weaponId: string): (string | null)[] {
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    return [
      stat?.attribute ? essencesMap.value.get(stat.attribute)?.type ?? null : null,
      stat?.secondary ? essencesMap.value.get(stat.secondary)?.type ?? null : null,
      stat?.skill ? essencesMap.value.get(stat.skill)?.type ?? null : null,
    ]
  }
  const weapon = weaponsMap.value.get(weaponId)
  return [
    weapon?.attributeStatId ? 'ATTRIBUTE' : null,
    weapon?.secondaryStatId ? 'SECONDARY' : null,
    weapon?.skillStatId ? 'SKILL' : null,
  ]
}

/** 从后端批量获取重合检测的等级比较结果 */
async function fetchOverlapCompareResults() {
  if (overlapItems.value.length === 0) return
  try {
    const results = new Map<number, number>()
    const res = await fetch('/api/profiles/compare_levels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: overlapItems.value.map((item) => {
          const customEntry = matrixEntryByWeaponId.value.get(item.customWeaponId)
          const matchedEntry = matrixEntryByWeaponId.value.get(item.matchedWeaponId)
          return {
            current_levels: [
              customEntry?.affix1_level ?? 0,
              customEntry?.affix2_level ?? 0,
              customEntry?.affix3_level ?? 0,
            ],
            existing_levels: [
              matchedEntry?.affix1_level ?? 0,
              matchedEntry?.affix2_level ?? 0,
              matchedEntry?.affix3_level ?? 0,
            ],
            stat_types: resolveStatTypes(item.customWeaponId),
          }
        }),
      }),
    })
    const data = await res.json()
    for (let i = 0; i < overlapItems.value.length; i++) {
      results.set(i, data.results?.[i] ?? 0)
    }
    overlapCompareResults.value = results
  } catch (error) {
    console.error('获取等级比较结果失败:', error)
  }
}

/** 获取预计算的比较结果：1（自定义更优）/ 0（相等）/ -1（内置更优） */
function getOverlapCompareResult(item: OverlapItem): number {
  const idx = overlapItems.value.indexOf(item)
  return overlapCompareResults.value.get(idx) ?? 0
}

/** 一键选择：根据比较结果自动选择动作 */
function autoSelectOverlap() {
  for (let i = 0; i < overlapItems.value.length; i++) {
    const item = overlapItems.value[i]
    if (!item) continue
    const cmp = overlapCompareResults.value.get(i) ?? 0
    if (cmp < 0) {
      item.action = 'delete'   // 自定义更小 → 删除自定义
    } else if (cmp === 0) {
      item.action = 'ignore'   // 相等 → 忽略
    } else {
      item.action = 'switch'   // 自定义更大 → 切换到内置
    }
  }
}

/**
 * 检查自定义基质与内置武器的词条重合
 * 匹配规则：三个槽位完全相等（含 null 对 null）
 * 检查范围：所有 config 中配置的自定义基质，无论是否在 profiles 中拥有
 */
function checkCustomOverlap() {
  const items: OverlapItem[] = []
  for (let i = 0; i < customStats.value.length; i++) {
    const stat = customStats.value[i]
    if (!stat) continue
    // 跳过已勾选"不再提示"的
    if (stat.no_prompt_switch) continue
    // 跳过属性全为空的条目（已被切换清空）
    if (!stat.attribute && !stat.secondary && !stat.skill) continue

    const syntheticId = `custom_stat_${i}`

    // 遍历所有内置武器，查找三词条完全匹配
    for (const [weaponId, weapon] of weaponsMap.value.entries()) {
      if (
        weapon.attributeStatId === stat.attribute &&
        weapon.secondaryStatId === stat.secondary &&
        weapon.skillStatId === stat.skill
      ) {
        items.push({
          customIndex: i,
          customName: stat.name || `自定义基质 ${i + 1}`,
          customWeaponId: syntheticId,
          matchedWeaponId: weaponId,
          matchedWeaponName: weapon.name,
          action: 'ignore',
        })
      }
    }
  }
  if (items.length === 0) return
  overlapItems.value = items
  overlapDialog.value = true
  fetchOverlapCompareResults()
}

/** 确认重合操作 */
async function confirmOverlapActions() {
  // 记录需要删除的自定义基质索引
  const indicesToDelete: number[] = []

  for (const item of overlapItems.value) {
    if (item.action === 'ignore') continue

    const stat = customStats.value[item.customIndex]
    if (!stat) continue

    if (item.action === 'suppress') {
      stat.no_prompt_switch = true
      await postCustomStatsUpdate()
    }

    if (item.action === 'switch') {
      // 切换 weapon_id，保留 affix 等级，优先级用武器稀有度默认值（不手动设置）
      const entry = matrixEntryByWeaponId.value.get(item.customWeaponId)
      if (entry) {
        const weapon = weaponsMap.value.get(item.matchedWeaponId)
        const newEntries = treasureMatrix.value
          .filter((e) => e.weapon_id !== item.customWeaponId)
          .concat({
            weapon_id: item.matchedWeaponId,
            weapon_name: weapon?.name || item.matchedWeaponName,
            affix1_level: entry.affix1_level,
            affix2_level: entry.affix2_level,
            affix3_level: entry.affix3_level,
            include_in_calculation: entry.include_in_calculation,
            // priority 不设置，使用武器稀有度默认值
          })
        await updateTreasureMatrix(newEntries)
      }
      indicesToDelete.push(item.customIndex)
    }

    if (item.action === 'delete') {
      // 删除自定义基质：从 treasure_matrix 中移除对应条目
      const newEntries = treasureMatrix.value.filter((e) => e.weapon_id !== item.customWeaponId)
      await updateTreasureMatrix(newEntries)
      indicesToDelete.push(item.customIndex)
    }
  }

  // 从大到小排序删除，避免索引偏移问题
  indicesToDelete.sort((a, b) => b - a)
  for (const index of indicesToDelete) {
    customStats.value.splice(index, 1)
  }

  // 更新 treasure_matrix 中所有引用后续自定义基质的索引
  if (indicesToDelete.length > 0) {
    const updatedTreasureMatrix = treasureMatrix.value.map((e) => {
      if (e.weapon_id.startsWith('custom_stat_')) {
        const currentIndex = Number.parseInt(e.weapon_id.replace('custom_stat_', ''), 10)
        // 计算删除后的新索引
        let newIndex = currentIndex
        for (const deletedIndex of indicesToDelete) {
          if (currentIndex > deletedIndex) {
            newIndex--
          }
        }
        if (newIndex !== currentIndex) {
          return { ...e, weapon_id: `custom_stat_${newIndex}` }
        }
      }
      return e
    })
    await updateTreasureMatrix(updatedTreasureMatrix)
    await postCustomStatsUpdate()
  }

  overlapDialog.value = false
  await fetchCustomStats()
}

onMounted(async () => {
  await fetchCustomStats()
  checkCustomOverlap()
})

const matrixEntryByWeaponId = computed(
  () => new Map(treasureMatrix.value.map((entry) => [entry.weapon_id, entry])),
)

// 武器总览会为每个图标多次判断拥有/满级状态，用 Set/Map 避免重复扫描 treasureMatrix。
const ownedWeaponIds = computed(() => new Set(matrixEntryByWeaponId.value.keys()))

const totalCount = computed(() =>
  weaponTypes.value.reduce((sum, wType) => sum + wType.weaponIds.length, 0),
)

const ownedCount = computed(() => ownedWeaponIds.value.size)

// 过滤后的武器类型列表
const filteredWeaponTypes = computed(() => {
  return weaponTypes.value
    .map((wType) => ({
      ...wType,
      weaponIds: wType.weaponIds
        .filter((weaponId) => {
          const weapon = weaponsMap.value.get(weaponId)
          if (!weapon) return false
          return selectedRarities.value.includes(String(weapon.rarity))
        })
        .toSorted((a, b) => {
          // 按稀有度降序排序（6★ -> 3★）
          const wa = weaponsMap.value.get(a)
          const wb = weaponsMap.value.get(b)
          if (wa && wb) return wb.rarity - wa.rarity
          return 0
        }),
    }))
    .filter((wType) => wType.weaponIds.length > 0)
})

function isWeaponOwned(weaponId: string): boolean {
  return ownedWeaponIds.value.has(weaponId)
}

function isWeaponMaxed(weaponId: string): boolean {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  return (
    entry !== undefined &&
    entry.affix1_level === 6 &&
    entry.affix2_level === 6 &&
    entry.affix3_level === 3
  )
}

async function toggleWeaponOwnership(weaponId: string) {
  if (isWeaponOwned(weaponId)) {
    await removeTreasureMatrixEntry(weaponId)
  } else {
    // 自定义条目使用配置中的名称，普通武器使用 weaponsMap 中的名称
    let weaponName: string
    if (isCustomEntry(weaponId)) {
      const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
      weaponName = customStats.value[index]?.name || `自定义基质 ${index + 1}`
    } else {
      const weapon = weaponsMap.value.get(weaponId)
      weaponName = weapon?.name || weaponId
    }
    await addTreasureMatrixEntry({
      weapon_id: weaponId,
      weapon_name: weaponName,
      affix1_level: 1,
      affix2_level: 1,
      affix3_level: 1,
      include_in_calculation: true,
    })
  }
}

/**
 * 显示武器详情弹窗（左键点击）
 */
function showWeaponDetail(weaponId: string) {
  detailWeaponId.value = weaponId
  detailDialog.value = true
}

/**
 * 获取武器属性文本
 * 自定义条目从 customStats 配置中读取属性名
 */
function getWeaponStatsText(weaponId: string): string {
  // 自定义条目：从配置中读取属性
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    if (!stat) return '自定义基质'
    const parts: string[] = []
    if (stat.attribute) parts.push(getGemTagName(stat.attribute))
    if (stat.secondary) parts.push(getGemTagName(stat.secondary))
    if (stat.skill) parts.push(getGemTagName(stat.skill))
    return parts.join('、') || '自定义基质'
  }

  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) return '未知武器'

  const parts: string[] = []
  if (weapon.attributeStatId) {
    parts.push(getGemTagName(weapon.attributeStatId))
  }
  if (weapon.secondaryStatId) {
    parts.push(getGemTagName(weapon.secondaryStatId))
  }
  if (weapon.skillStatId) {
    parts.push(getGemTagName(weapon.skillStatId))
  }

  return parts.join('、') || '无属性'
}

/**
 * 获取同类武器（相同属性组合）
 * 自定义条目没有真实武器数据，返回空数组
 */
function getSameStatWeapons(weaponId: string): string[] {
  if (isCustomEntry(weaponId)) return []
  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) return []
  const sameWeapons: string[] = []
  for (const [id, w] of weaponsMap.value.entries()) {
    if (
      id !== weaponId &&
      w.attributeStatId === weapon.attributeStatId &&
      w.secondaryStatId === weapon.secondaryStatId &&
      w.skillStatId === weapon.skillStatId
    ) {
      sameWeapons.push(id)
    }
  }
  return sameWeapons
}

/**
 * 判断武器是否"可切换"：存在同属性、更高优先级、且已拥有的武器
 */
function isSwitchable(weaponId: string): boolean {
  const myPriority = getWeaponPriority(weaponId)
  const sameWeapons = getSameStatWeapons(weaponId)
  return sameWeapons.some(
    (id) => isWeaponOwned(id) && getWeaponPriority(id) >= myPriority,
  )
}

/**
 * 获取可切换的目标武器是否满级（用于灰色呼吸动画）
 */
function isSwitchTargetMaxed(weaponId: string): boolean {
  const myPriority = getWeaponPriority(weaponId)
  const sameWeapons = getSameStatWeapons(weaponId)
  return sameWeapons.some(
    (id) =>
      isWeaponOwned(id)
      && getWeaponPriority(id) >= myPriority
      && isWeaponMaxed(id),
  )
}

/**
 * 获取武器的基质等级文本
 */
function getMatrixLevelText(weaponId: string): string {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  if (!entry) return '未配置'
  return `+${entry.affix1_level} / +${entry.affix2_level} / +${entry.affix3_level}`
}

/**
 * 获取用户手动设置的优先级（0 表示未设置）
 */
function getUserPriority(weaponId: string): number {
  const profilePriority = activeProfile.value.weapon_priorities?.[weaponId]
  if (profilePriority && profilePriority > 0) return profilePriority
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  return entry?.priority || 0
}

/**
 * 获取武器的有效优先级（未设置时使用稀有度）
 * 自定义条目默认优先级为 6（等同于 6★）
 */
function getWeaponPriority(weaponId: string): number {
  const userP = getUserPriority(weaponId)
  if (userP > 0) return userP
  // 自定义条目默认优先级为 6
  if (isCustomEntry(weaponId)) return 6
  const weapon = weaponsMap.value.get(weaponId)
  return weapon ? weapon.rarity : 0
}

function getEffectivePriorityForSwap(weaponId: string, entry?: TreasureMatrixEntry): number {
  const userPriority = getUserPriority(weaponId) || entry?.priority || 0
  if (userPriority > 0) return userPriority
  const weapon = weaponsMap.value.get(weaponId)
  return weapon ? weapon.rarity : 0
}

/**
 * 交换两把武器的基质数据
 */
async function swapMatrix(weaponAId: string, weaponBId: string) {
  const entries = treasureMatrix.value.map((entry) => ({ ...entry }))
  const entryA = entries.find((e) => e.weapon_id === weaponAId)
  const entryB = entries.find((e) => e.weapon_id === weaponBId)

  const weaponA = weaponsMap.value.get(weaponAId)
  const weaponB = weaponsMap.value.get(weaponBId)

  const hasA = !!entryA
  const hasB = !!entryB

  if (!hasA && !hasB) return

  const priorityA = getEffectivePriorityForSwap(weaponAId, entryA)
  const priorityB = getEffectivePriorityForSwap(weaponBId, entryB)

  if (hasA && !hasB) {
    // A有基质、B无基质 → A移除、B添加A的数据
    const nextEntries = entries
      .filter((entry) => entry.weapon_id !== weaponAId)
      .concat({
        ...entryA!,
        weapon_id: weaponBId,
        weapon_name: weaponB?.name || weaponBId,
        priority: priorityA,
      })
    await updateTreasureMatrix(nextEntries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  } else if (!hasA && hasB) {
    // A无基质、B有基质 → A添加B的数据、B移除
    const nextEntries = entries
      .filter((entry) => entry.weapon_id !== weaponBId)
      .concat({
        ...entryB!,
        weapon_id: weaponAId,
        weapon_name: weaponA?.name || weaponAId,
        priority: priorityB,
      })
    await updateTreasureMatrix(nextEntries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  } else {
    // 两者都有基质，交换等级、计算开关和有效优先级
    const matrixA = {
      affix1: entryA!.affix1_level,
      affix2: entryA!.affix2_level,
      affix3: entryA!.affix3_level,
      includeInCalculation: entryA!.include_in_calculation,
    }
    entryA!.affix1_level = entryB!.affix1_level
    entryA!.affix2_level = entryB!.affix2_level
    entryA!.affix3_level = entryB!.affix3_level
    entryA!.include_in_calculation = entryB!.include_in_calculation
    entryA!.priority = priorityB

    entryB!.affix1_level = matrixA.affix1
    entryB!.affix2_level = matrixA.affix2
    entryB!.affix3_level = matrixA.affix3
    entryB!.include_in_calculation = matrixA.includeInCalculation
    entryB!.priority = priorityA

    await updateTreasureMatrix(entries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  }

  // 关闭弹窗
  detailDialog.value = false
}
</script>

<style scoped lang="scss">
.group-icon {
  width: 1.5rem;
  height: 1.5rem;
  vertical-align: middle;
}

.essence-icon-small {
  width: 1.5rem;
  height: 1.5rem;
  vertical-align: middle;
  border-radius: 4px;
}

.weapon-overview-container {
  position: relative;
}

.connection-lines-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
  overflow: visible;
}

.connection-line {
  position: absolute;
  height: 2px;
  background-color: rgb(24, 103, 192);
  transform-origin: 0 50%;
  opacity: 0;
  transition: opacity 0.2s ease;

  &::before {
    content: '';
    position: absolute;
    right: -4px;
    top: -3px;
    width: 8px;
    height: 8px;
    background-color: rgb(24, 103, 192);
    border-radius: 50%;
    box-shadow: 0 0 8px rgb(24, 103, 192);
  }

  &[style*="opacity: 1"] {
    opacity: 1;
  }
}

.weapon-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(3.5rem, 1fr));
  gap: 0.5rem;
}

.weapon-add-button {
  width: 100%;
  height: 100%;
  cursor: pointer;
  border: 2px dashed rgba(var(--v-theme-on-surface), 0.25);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s, background 0.15s;

  &:hover {
    border-color: rgba(var(--v-theme-primary), 0.6);
    background: rgba(var(--v-theme-primary), 0.05);
  }
}

// --- 详情弹窗等级编辑样式 ---
.detail-level-section {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.detail-attr-control {
  flex: 1;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 12px;
  transition: background 0.18s;

  &:hover {
    background: rgba(var(--v-theme-on-surface), 0.03);
  }
}

.detail-attr-label {
  color: rgba(var(--v-theme-on-surface), 0.52);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-attr-pips {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 20px;
}

.detail-pip {
  width: 10px;
  height: 20px;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.12);
  cursor: pointer;
  transition: background 0.18s, box-shadow 0.18s, transform 0.18s;

  &:hover {
    transform: translateY(-1px) scaleY(1.08);
  }
}

.detail-attr-control--primary .detail-pip.active {
  background: rgb(var(--v-theme-primary));
  box-shadow: 0 2px 7px rgba(var(--v-theme-primary), 0.32);
}

.detail-attr-control--teal .detail-pip.active {
  background: #48a9a6;
  box-shadow: 0 2px 7px rgba(72, 169, 166, 0.34);
}

.detail-attr-control--indigo .detail-pip.active {
  background: #5c6bc0;
  box-shadow: 0 2px 7px rgba(92, 107, 192, 0.34);
}

.detail-pip.detail-pip--max.active {
  animation: detailPipPulse 2.2s ease-in-out infinite;
}

.detail-attr-value {
  color: rgba(var(--v-theme-on-surface), 0.68);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  font-weight: 800;
}

.detail-attr-value--full {
  color: rgb(var(--v-theme-primary));
}

@keyframes detailPipPulse {
  0%, 100% {
    transform: scaleY(1);
    filter: brightness(1);
  }
  50% {
    transform: scaleY(1.08);
    filter: brightness(1.18);
  }
}

.weapon-overview-item {
  width: 3.5rem;
  height: 3.5rem;
  cursor: pointer;
  position: relative;

  &:hover .weapon-icon-wrapper {
    transform: scale(1.05);
  }
}

.weapon-icon-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  transition:
    transform 0.15s,
    opacity 0.15s,
    filter 0.15s;
  border-radius: 6px;
  overflow: hidden;

  // 未拥有：灰色滤镜必须作用于上级容器，标记作为兄弟节点避免被叠加影响
  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }

  // 可切换目标满级：灰色呼吸背景
  &.switch-target-maxed {
    animation: switch-target-breathe 2s ease-in-out infinite;
  }

  // 已满级：彩虹边框动画（优先级最高，必须在 switch-target-maxed 之后定义以覆盖）
  &.weapon-maxed {
    animation: rainbow-glow 3s linear infinite;
  }
}

// 左上角缩小版圆形基质图标（底板+技能叠加）
.weapon-matrix-badge {
  position: absolute;
  top: -3px;
  left: -3px;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 50%;
  overflow: hidden;
  z-index: 5;
  pointer-events: none;
  border: 1.5px solid rgba(255, 255, 255, 0);
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  // 中号模式：2倍大小
  &--medium {
    width: 2.4rem;
    height: 2.4rem;
    top: -5.3px;
    left: -5.3px;
    z-index: 5;
  }
}

.weapon-matrix-badge-bg {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.weapon-matrix-badge-skill {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 1;
  transform: translate(5%, -5%);
}

// 可切换小橙点（通知 badge 样式）
.switch-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff7100;
  z-index: 5;
  pointer-events: none;
  box-shadow: 0 0 4px rgba(255, 113, 0, 0.6);
}

// 未拥有斜向胶带遮罩（弹窗内等级区域）
.detail-level-wrapper {
  position: relative;
}

.not-owned-tape-detail {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 110%;
  height: 24px;
  background: linear-gradient(
    135deg,
    rgba(255, 193, 7, 0.95) 0%,
    rgba(255, 193, 7, 0.88) 40%,
    rgba(255, 193, 7, 0.80) 100%
  );
  transform: translate(-50%, -50%) rotate(-8deg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.not-owned-tape-detail-text {
  color: rgba(0, 0, 0, 0.8);
  font-size: 0.8rem;
  font-weight: 900;
  letter-spacing: 0.2em;
  white-space: nowrap;
}

// 撕开胶布动画（左到右渐出/渐入）
.tape-peel-enter-active {
  animation: tape-peel-in 0.2s ease-out forwards;
}

.tape-peel-leave-active {
  animation: tape-peel-out 0.2s ease-in forwards;
}

@keyframes tape-peel-in {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0 0 0 0);
  }
}

@keyframes tape-peel-out {
  from {
    clip-path: inset(0 0 0 0);
  }
  to {
    clip-path: inset(0 0 0 100%);
  }
}

// 未拥有遮罩层：覆盖等级区域，阻止点击
.detail-level-outer {
  position: relative;
}

.not-owned-block-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 6;
  cursor: pointer;
}

.weapon-icon-detail {
  width: 3rem !important;
  height: 3rem !important;
}

.weapon-icon-same {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}

.weapon-icon-overlap {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}

.overlap-icon-wrapper {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;

  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }
}

.rainbow-border {
  position: absolute;
  inset: -3px;
  border-radius: 8px;
  background: linear-gradient(45deg, #FFF, #ff4ada, #ff4e4e, #ff9832, #ff0, #0f0, #00ffff, #79a0fd, #d46eff, #ff8df0, #FFF);
  background-size: 400% 400%;
  animation: rainbow-rotate 3s linear infinite;
  z-index: -1;
  pointer-events: none;
}

@keyframes rainbow-rotate {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes rainbow-glow {
  0%,
  100% {
    box-shadow: 0 0 10px rgba(255, 0, 0, 0.8);
  }
  14% {
    box-shadow: 0 0 10px rgba(255, 127, 0, 0.8);
  }
  28% {
    box-shadow: 0 0 10px rgba(255, 255, 0, 0.8);
  }
  42% {
    box-shadow: 0 0 10px rgba(0, 255, 0, 0.8);
  }
  57% {
    box-shadow: 0 0 10px rgba(0, 0, 255, 0.8);
  }
  71% {
    box-shadow: 0 0 10px rgba(75, 0, 130, 0.8);
  }
  85% {
    box-shadow: 0 0 10px rgba(148, 0, 211, 0.8);
  }
}

.switchable-badge {
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 6;
  pointer-events: none;
  font-size: 0.55rem !important;
  height: 14px !important;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.35);
}


@keyframes switch-target-breathe {
  0%,
  100% {
    box-shadow: 0 0 8px 2px rgba(128, 128, 128, 0.3);
  }
  50% {
    box-shadow: 0 0 14px 5px rgba(158, 158, 158, 0.85);
  }
}
</style>
