/**
 * 武器状态查询组合式函数。
 *
 * 提供武器的各种状态查询方法，包括拥有状态、满级判断、优先级计算等。
 */

import type { TreasureMatrixEntry } from '@/composables/useProfiles'
import { computed } from 'vue'
import { useProfiles } from '@/composables/useProfiles'
import { useStaticData } from '@/utils/gameData/staticData'

export function useWeaponStats() {
  const { activeProfile, treasureMatrix } = useProfiles()
  const { weaponsMap } = useStaticData()

  // 核心索引：weapon_id -> TreasureMatrixEntry
  const matrixEntryByWeaponId = computed(
    () => new Map(treasureMatrix.value.map((entry) => [entry.weapon_id, entry])),
  )

  // 已拥有的武器 ID 集合
  const ownedWeaponIds = computed(() => new Set(matrixEntryByWeaponId.value.keys()))

  /**
   * 判断武器是否已拥有
   */
  function isWeaponOwned(weaponId: string): boolean {
    return ownedWeaponIds.value.has(weaponId)
  }

  /**
   * 判断武器是否满级（6/6/3）
   */
  function isWeaponMaxed(weaponId: string): boolean {
    const entry = matrixEntryByWeaponId.value.get(weaponId)
    return (
      entry !== undefined &&
      entry.affix1_level === 6 &&
      entry.affix2_level === 6 &&
      entry.affix3_level === 3
    )
  }

  /**
   * 判断是否为自定义基质条目（weapon_id 以 custom_stat_ 开头）
   */
  function isCustomEntry(weaponId: string | null): boolean {
    return weaponId?.startsWith('custom_stat_') ?? false
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

  /**
   * 获取交换时的有效优先级
   */
  function getEffectivePriorityForSwap(weaponId: string, entry?: TreasureMatrixEntry): number {
    const userPriority = getUserPriority(weaponId) || entry?.priority || 0
    if (userPriority > 0) return userPriority
    const weapon = weaponsMap.value.get(weaponId)
    return weapon ? weapon.rarity : 0
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

  return {
    // 状态
    matrixEntryByWeaponId,
    ownedWeaponIds,
    treasureMatrix,

    // 查询方法
    isWeaponOwned,
    isWeaponMaxed,
    isCustomEntry,
    getUserPriority,
    getWeaponPriority,
    getEffectivePriorityForSwap,
    getSameStatWeapons,
    isSwitchable,
    isSwitchTargetMaxed,
    getMatrixLevelText,
  }
}
