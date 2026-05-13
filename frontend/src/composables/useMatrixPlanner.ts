/**
 * 基质规划器组合式函数。
 *
 * 改编自 ef-frontend-v1 的基质计算器逻辑，帮助用户找到刷取所需基质的最佳位置。
 */

import { computed, onUnmounted, ref, type Ref, watch } from 'vue'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'
import { safeLoadJson, safeSetJson } from '@/utils/safeStorage'

let _nextId = 1

export interface PlannerEssenceStat {
  /** 唯一标识符，用于 v-for key 和稳定引用 */
  id: number
  isCustom: boolean
  weaponId: string | null
  attribute: string | null
  secondary: string | null
  skill: string | null
}

export interface BattleChoice {
  battleId: string
  battleName: string
  selectedAttribute: string[]
  selectedSecondary: string | null
  selectedSkill: string | null
  matchedSelectedIndices: number[]
  matchedWeaponIds: string[]
}

export interface EnergyAlluvium {
  battleId: string
  battleName: string
  imageUrl?: string
  secondaryStats: string[]
  skillStats: string[]
}

interface PlannerWeaponStats {
  weaponId: string
  attribute: string
  secondary: string
  skill: string
}

/** 淤积点名称前缀，显示时裁掉 */
const ALLUVIUM_PREFIX = '重度能量淤积点·'

/**
 * 将完整淤积点名称裁剪为短显示名。
 * 例如 "重度能量淤积点·枢纽区" → "枢纽区"
 */
export function getDisplayName(battleName: string): string {
  return battleName.startsWith(ALLUVIUM_PREFIX)
    ? battleName.slice(ALLUVIUM_PREFIX.length)
    : battleName
}

// 能量淤积点数据（刷取位置）
// 格式与 ef-frontend-v1 的 custom/core/weaponEssence.ts 保持一致，便于手动同步。
// 更新时直接从 weaponEssence.ts 的 energyAlluviums 复制即可。
const energyAlluviums: Record<string, EnergyAlluvium> = {
  '重度能量淤积点·枢纽区': {
    battleId: '重度能量淤积点·枢纽区',
    battleName: '重度能量淤积点·枢纽区',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map01_lv001_1.webp',
    secondaryStats: [
      '攻击提升', '灼热伤害提升', '电磁伤害提升', '寒冷伤害提升',
      '自然伤害提升', '源石技艺提升', '终结技充能效率提升', '法术伤害提升',
    ],
    skillStats: ['强攻', '压制', '追袭', '粉碎', '巧技', '迸发', '流转', '效益'],
  },
  '重度能量淤积点·源石研究园': {
    battleId: '重度能量淤积点·源石研究园',
    battleName: '重度能量淤积点·源石研究园',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map01_lv005_1.webp',
    secondaryStats: [
      '攻击提升', '物理伤害提升', '电磁伤害提升', '寒冷伤害提升',
      '自然伤害提升', '暴击率提升', '终结技充能效率提升', '法术伤害提升',
    ],
    skillStats: ['压制', '追袭', '昂扬', '巧技', '附术', '医疗', '切骨', '效益'],
  },
  '重度能量淤积点·矿脉源区': {
    battleId: '重度能量淤积点·矿脉源区',
    battleName: '重度能量淤积点·矿脉源区',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map01_lv006_1.webp',
    secondaryStats: [
      '生命提升', '物理伤害提升', '灼热伤害提升', '寒冷伤害提升',
      '自然伤害提升', '暴击率提升', '源石技艺提升', '治疗效率提升',
    ],
    skillStats: ['强攻', '压制', '巧技', '残暴', '附术', '迸发', '夜幕', '效益'],
  },
  '重度能量淤积点·供能高地': {
    battleId: '重度能量淤积点·供能高地',
    battleName: '重度能量淤积点·供能高地',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map01_lv007_1.webp',
    secondaryStats: [
      '攻击提升', '生命提升', '物理伤害提升', '灼热伤害提升',
      '自然伤害提升', '暴击率提升', '源石技艺提升', '治疗效率提升',
    ],
    skillStats: ['追袭', '粉碎', '昂扬', '残暴', '附术', '医疗', '切骨', '流转'],
  },
  '重度能量淤积点·武陵城': {
    battleId: '重度能量淤积点·武陵城',
    battleName: '重度能量淤积点·武陵城',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map02_lv002_1.webp',
    secondaryStats: [
      '攻击提升', '生命提升', '电磁伤害提升', '寒冷伤害提升',
      '暴击率提升', '终结技充能效率提升', '法术伤害提升', '治疗效率提升',
    ],
    skillStats: ['强攻', '粉碎', '残暴', '医疗', '切骨', '迸发', '夜幕', '流转'],
  },
  '重度能量淤积点·清波寨': {
    battleId: '重度能量淤积点·清波寨',
    battleName: '重度能量淤积点·清波寨',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map02_lv003_1.webp',
    secondaryStats: [
      '生命提升', '物理伤害提升', '电磁伤害提升', '寒冷伤害提升',
      '源石技艺提升', '终结技充能效率提升', '法术伤害提升', '治疗效率提升',
    ],
    skillStats: ['压制', '粉碎', '昂扬', '巧技', '医疗', '切骨', '迸发', '夜幕'],
  },
  '重度能量淤积点·首墩': {
    battleId: '重度能量淤积点·首墩',
    battleName: '重度能量淤积点·首墩',
    imageUrl:
      'https://cos.yituliu.cn/endfield/endfielddata/assets/beyond/dynamicassets/gameplay/ui/sprites/loading/bg_loading_map02_lv003_1.webp',
    secondaryStats: [
      '攻击提升', '物理伤害提升', '灼热伤害提升', '电磁伤害提升',
      '自然伤害提升', '暴击率提升', '终结技充能效率提升', '法术伤害提升',
    ],
    skillStats: ['强攻', '追袭', '昂扬', '残暴', '附术', '夜幕', '流转', '效益'],
  },
}

// 所有属性词条
const allAttributeStats = ['敏捷提升', '力量提升', '意志提升', '智识提升', '主能力提升']
const allAttributeCombinations = combinations(allAttributeStats, 3)

// 所有副属性词条
const allSecondaryStats = [
  '攻击提升', '生命提升', '物理伤害提升', '灼热伤害提升', '电磁伤害提升',
  '寒冷伤害提升', '自然伤害提升', '暴击率提升', '源石技艺提升',
  '终结技充能效率提升', '法术伤害提升', '治疗效率提升',
]

// 所有技能词条
const allSkillStats = [
  '强攻', '压制', '追袭', '粉碎', '昂扬', '巧技', '残暴',
  '附术', '医疗', '切骨', '迸发', '夜幕', '流转', '效益',
]

function combinations<T>(arr: T[], size: number): T[][] {
  if (size === 0) return [[]]
  if (arr.length < size) return []
  const result: T[][] = []
  for (let index = 0; index <= arr.length - size; index++) {
    const rest = arr.slice(index + 1)
    for (const combo of combinations(rest, size - 1)) {
      result.push([arr[index]!, ...combo])
    }
  }
  return result
}

function getStatDisplayName(statId: string | null): string {
  if (!statId) return ''
  return getGemTagName(statId)
}

function clearAllStats(requiredEssenceStats: Ref<PlannerEssenceStat[]>, lastSelectedWeaponId: Ref<string | null>) {
  requiredEssenceStats.value = []
  lastSelectedWeaponId.value = null
}

/** 将单个需求词条与战斗可用词条进行匹配。 */
function requirementMatchesBattle(
  stat: PlannerEssenceStat,
  selectedAttributes: string[],
  selectedSecondary: string | null,
  selectedSkill: string | null,
  battleSecondaryStats: string[],
  battleSkillStats: string[],
): boolean {
  if (!stat.attribute || !stat.secondary || !stat.skill) return false
  if (!selectedAttributes.includes(stat.attribute)) return false
  if (selectedSecondary !== null) {
    return stat.secondary === selectedSecondary && battleSkillStats.includes(stat.skill)
  }
  if (selectedSkill !== null) {
    return battleSecondaryStats.includes(stat.secondary) && stat.skill === selectedSkill
  }
  return false
}

/** 查找匹配战斗词条组合的所有武器。 */
function findMatchingWeapons(
  weaponStats: PlannerWeaponStats[],
  selectedAttributes: string[],
  battleSecondaryStats: string[],
  battleSkillStats: string[],
  selectedSecondary: string | null,
  selectedSkill: string | null,
): string[] {
  const matched: string[] = []
  for (const weapon of weaponStats) {
    if (!selectedAttributes.includes(weapon.attribute)) continue
    const secOk = selectedSecondary !== null
      ? weapon.secondary === selectedSecondary
      : battleSecondaryStats.includes(weapon.secondary)
    const skillOk = selectedSkill !== null
      ? weapon.skill === selectedSkill
      : battleSkillStats.includes(weapon.skill)
    if (secOk && skillOk) matched.push(weapon.weaponId)
  }
  return matched
}

export function useMatrixPlanner() {
  const { weaponsMap } = useStaticData()

  // 规划计算会反复按词条匹配武器，先把武器 ID 转成显示词条，避免在每个方案里重复转换。
  const weaponPlannerStats = computed<PlannerWeaponStats[]>(() => {
    const rows: PlannerWeaponStats[] = []
    for (const [weaponId, weapon] of weaponsMap.value.entries()) {
      const attribute = getStatDisplayName(weapon.attributeStatId)
      const secondary = getStatDisplayName(weapon.secondaryStatId)
      const skill = getStatDisplayName(weapon.skillStatId)
      if (!attribute || !secondary || !skill) continue
      rows.push({ weaponId, attribute, secondary, skill })
    }
    return rows
  })

  // 从localStorage加载保存的状态；坏缓存会被清理，避免页面初始化白屏。
  const initialStats = safeLoadJson<PlannerEssenceStat[]>('matrixPlannerStats', [])
  _nextId = Math.max(
    _nextId,
    Math.max(
      0,
      ...initialStats
        .map((stat) => stat.id)
        .filter((id): id is number => typeof id === 'number'),
    ) + 1,
  )

  const requiredEssenceStats = ref<PlannerEssenceStat[]>(initialStats)
  const lastSelectedWeaponId = ref<string | null>(null)
  let saveStatsTimer: number | undefined

  // 监听变化并保存到localStorage
  watch(
    requiredEssenceStats,
    (newStats) => {
      window.clearTimeout(saveStatsTimer)
      saveStatsTimer = window.setTimeout(() => {
        safeSetJson('matrixPlannerStats', newStats)
      }, 300)
    },
    { deep: true },
  )

  onUnmounted(() => {
    window.clearTimeout(saveStatsTimer)
  })

  function addStatFromWeapon(weaponId: string) {
    const weapon = weaponsMap.value.get(weaponId)
    if (!weapon) return

    // 记录最后选择的武器
    lastSelectedWeaponId.value = weaponId

    // 检查是否已添加 — 切换关闭
    const existing = requiredEssenceStats.value.findIndex(
      (s) => !s.isCustom && s.weaponId === weaponId,
    )
    if (existing !== -1) {
      requiredEssenceStats.value.splice(existing, 1)
      return
    }
    // 存储显示名（而非内部 ID），确保与 allAttributeStats 等匹配一致
    requiredEssenceStats.value.push({
      id: _nextId++,
      isCustom: false,
      weaponId,
      attribute: getStatDisplayName(weapon.attributeStatId),
      secondary: getStatDisplayName(weapon.secondaryStatId),
      skill: getStatDisplayName(weapon.skillStatId),
    })
  }

  function addCustomStat() {
    requiredEssenceStats.value.push({
      id: _nextId++,
      isCustom: true,
      weaponId: null,
      attribute: null,
      secondary: null,
      skill: null,
    })
  }

  function removeStat(index: number) {
    requiredEssenceStats.value.splice(index, 1)
  }

  function moveStatUp(index: number) {
    if (index === 0) return
    const item = requiredEssenceStats.value.splice(index, 1)[0]!
    requiredEssenceStats.value.splice(index - 1, 0, item)
  }

  function moveStatDown(index: number) {
    if (index === requiredEssenceStats.value.length - 1) return
    const item = requiredEssenceStats.value.splice(index, 1)[0]!
    requiredEssenceStats.value.splice(index + 1, 0, item)
  }

  function getEssenceStatDescription(stat: PlannerEssenceStat): string {
    if (stat.isCustom) return '自定义'
    if (stat.weaponId) {
      const weapon = weaponsMap.value.get(stat.weaponId)
      return weapon ? weapon.name : stat.weaponId
    }
    return '未知'
  }

  function buildChoiceForSecondary(
    battleId: string,
    battleName: string,
    selectedAttribute: string[],
    selectedSecondary: string,
    battleSkillStats: string[],
  ): BattleChoice | undefined {
    const matchedSelectedIndices: number[] = []
    for (const [index, stat] of requiredEssenceStats.value.entries()) {
      if (requirementMatchesBattle(stat, selectedAttribute, selectedSecondary, null, [], battleSkillStats)) {
        matchedSelectedIndices.push(index)
      }
    }
    if (matchedSelectedIndices.length === 0) return undefined
    const matchedWeaponIds = findMatchingWeapons(
      weaponPlannerStats.value,
      selectedAttribute,
      [],
      battleSkillStats,
      selectedSecondary,
      null,
    )
    return { battleId, battleName, selectedAttribute, selectedSecondary, selectedSkill: null, matchedSelectedIndices, matchedWeaponIds }
  }

  function buildChoiceForSkill(
    battleId: string,
    battleName: string,
    selectedAttribute: string[],
    selectedSkill: string,
    battleSecondaryStats: string[],
  ): BattleChoice | undefined {
    const matchedSelectedIndices: number[] = []
    for (const [index, stat] of requiredEssenceStats.value.entries()) {
      if (requirementMatchesBattle(stat, selectedAttribute, null, selectedSkill, battleSecondaryStats, [])) {
        matchedSelectedIndices.push(index)
      }
    }
    if (matchedSelectedIndices.length === 0) return undefined
    const matchedWeaponIds = findMatchingWeapons(
      weaponPlannerStats.value,
      selectedAttribute,
      battleSecondaryStats,
      [],
      null,
      selectedSkill,
    )
    return { battleId, battleName, selectedAttribute, selectedSecondary: null, selectedSkill, matchedSelectedIndices, matchedWeaponIds }
  }

  const battleChoices = ref<BattleChoice[]>([])

  /**
   * 重新计算所有可能的刷取方案。
   * 遍历每个能量淤积点，对每个地点生成所有 3 属性组合（共 C(5,3)=10 种），
   * 再分别与该地点的附加属性、技能属性配对，筛选出至少满足一项需求的方案。
   */
  function _recomputeChoices() {
    const result: BattleChoice[] = []
    for (const { battleId, battleName, secondaryStats, skillStats } of Object.values(energyAlluviums)) {
      for (const selectedAttribute of allAttributeCombinations) {
        for (const selectedSecondary of secondaryStats) {
          const choice = buildChoiceForSecondary(battleId, battleName, selectedAttribute, selectedSecondary, skillStats)
          if (choice) result.push(choice)
        }
        for (const selectedSkill of skillStats) {
          const choice = buildChoiceForSkill(battleId, battleName, selectedAttribute, selectedSkill, secondaryStats)
          if (choice) result.push(choice)
        }
      }
    }
    battleChoices.value = result
  }

  watch(
    requiredEssenceStats,
    () => _recomputeChoices(),
    { deep: true, immediate: true },
  )

  /** 按优先级排序后的所有有效方案：满足需求数 > 匹配已选武器数 > 匹配武器总数 */
  const _sortedChoices = computed(() => {
    const filtered = battleChoices.value.filter(
      ({ matchedSelectedIndices }) => matchedSelectedIndices.length > 0,
    )

    const selectedWeaponIds = new Set(
      requiredEssenceStats.value
        .filter(stat => !stat.isCustom && stat.weaponId)
        .map(stat => stat.weaponId!)
    )

    filtered.sort((a, b) => {
      // 优先：满足更多需求
      if (b.matchedSelectedIndices.length !== a.matchedSelectedIndices.length) {
        return b.matchedSelectedIndices.length - a.matchedSelectedIndices.length
      }

      // 其次：匹配更多已选择的武器
      const aMatchedSelected = a.matchedWeaponIds.filter(id => selectedWeaponIds.has(id)).length
      const bMatchedSelected = b.matchedWeaponIds.filter(id => selectedWeaponIds.has(id)).length
      if (aMatchedSelected !== bMatchedSelected) {
        return bMatchedSelected - aMatchedSelected
      }

      // 最后：匹配武器总数
      return b.matchedWeaponIds.length - a.matchedWeaponIds.length
    })
    return filtered
  })

  /** 最优的前 5 个方案（使用预刻券模式） */
  const bestChoices = computed(() => _sortedChoices.value.slice(0, 5))

  /** 所有有效方案（不使用预刻券模式） */
  const allChoices = computed(() => _sortedChoices.value)

  return {
    requiredEssenceStats,
    lastSelectedWeaponId,
    allAttributeStats,
    allSecondaryStats,
    allSkillStats,
    energyAlluviums,
    addStatFromWeapon,
    addCustomStat,
    removeStat,
    moveStatUp,
    moveStatDown,
    getEssenceStatDescription,
    getStatDisplayName,
    battleChoices,
    bestChoices,
    allChoices,
    clearAllStats: () => clearAllStats(requiredEssenceStats, lastSelectedWeaponId),
  }
}
