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
        点击武器图标可切换是否拥有该武器的基质。已满级（6/6/3）的武器会显示彩虹边框。
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
        </v-chip-group>
      </div>

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
            :class="{
              'weapon-not-owned': !isWeaponOwned(weaponId),
              'weapon-maxed': isWeaponMaxed(weaponId),
            }"
            @click="toggleWeaponOwnership(weaponId)"
          >
            <item-icon :item-id="weaponId" show-item-name />

            <!-- 满级的彩虹边框 -->
            <div v-if="isWeaponMaxed(weaponId)" class="rainbow-border" />
          </div>
        </div>
      </template>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { useProfiles } from '@/composables/useProfiles'
import { useStaticData } from '@/utils/gameData/staticData'

const { weaponTypes, weaponsMap } = useStaticData()
const {
  activeProfile,
  treasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  updateWeaponOverviewFilters,
} = useProfiles()

const ownedWeaponIds = computed(() => treasureMatrix.value.map((e) => e.weapon_id))

const totalCount = computed(() =>
  weaponTypes.value.reduce((sum, wType) => sum + wType.weaponIds.length, 0),
)

const ownedCount = computed(() => ownedWeaponIds.value.length)

// 星级过滤器
const selectedRarities = ref<string[]>(['3', '4', '5', '6'])

// 从profile加载过滤器设置
watch(
  () => activeProfile.value.weapon_overview_filters,
  (filters) => {
    if (filters) {
      const newRarities: string[] = []
      if (filters['3star']) newRarities.push('3')
      if (filters['4star']) newRarities.push('4')
      if (filters['5star']) newRarities.push('5')
      if (filters['6star']) newRarities.push('6')

      // 只有在实际不同时才更新，避免循环
      const current = selectedRarities.value.toSorted().join(',')
      const updated = newRarities.toSorted().join(',')
      if (current !== updated) {
        selectedRarities.value = newRarities
      }
    }
  },
  { immediate: true },
)

// 保存过滤器设置
watch(
  selectedRarities,
  async (newValue, oldValue) => {
    // 避免初始化时触发
    if (!oldValue) return

    // 检查是否真的有变化
    const oldSorted = oldValue.toSorted().join(',')
    const newSorted = newValue.toSorted().join(',')
    if (oldSorted === newSorted) return

    await updateWeaponOverviewFilters({
      '3star': newValue.includes('3'),
      '4star': newValue.includes('4'),
      '5star': newValue.includes('5'),
      '6star': newValue.includes('6'),
    })
  },
  { deep: true },
)

// 过滤后的武器类型列表
const filteredWeaponTypes = computed(() => {
  return weaponTypes.value
    .map((wType) => ({
      ...wType,
      weaponIds: wType.weaponIds.filter((weaponId) => {
        const weapon = weaponsMap.value.get(weaponId)
        if (!weapon) return false
        return selectedRarities.value.includes(String(weapon.rarity))
      }),
    }))
    .filter((wType) => wType.weaponIds.length > 0)
})

function isWeaponOwned(weaponId: string): boolean {
  return ownedWeaponIds.value.includes(weaponId)
}

function isWeaponMaxed(weaponId: string): boolean {
  const entry = treasureMatrix.value.find((e) => e.weapon_id === weaponId)
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
    const weapon = weaponsMap.value.get(weaponId)
    await addTreasureMatrixEntry({
      weapon_id: weaponId,
      weapon_name: weapon?.name || weaponId,
      affix1_level: 1,
      affix2_level: 1,
      affix3_level: 1,
      include_in_calculation: true,
    })
  }
}
</script>

<style scoped lang="scss">
.group-icon {
  width: 1.5rem;
  height: 1.5rem;
  vertical-align: middle;
}

.weapon-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(3.5rem, 1fr));
  gap: 0.5rem;
}

.weapon-overview-item {
  width: 3.5rem;
  height: 3.5rem;
  cursor: pointer;
  position: relative;
  transition:
    transform 0.15s,
    opacity 0.15s;
  border-radius: 6px;

  &:hover {
    transform: scale(1.05);
  }

  // 未拥有：半透明灰色层
  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }

  // 已满级：彩虹边框动画
  &.weapon-maxed {
    animation: rainbow-glow 3s linear infinite;
  }
}

.rainbow-border {
  position: absolute;
  inset: -3px;
  border-radius: 8px;
  background: linear-gradient(
    45deg,
    #ff0000,
    #ff7f00,
    #ffff00,
    #00ff00,
    #0000ff,
    #4b0082,
    #9400d3
  );
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
</style>
