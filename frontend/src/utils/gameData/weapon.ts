import { useStaticData } from '@/utils/gameData/staticData'

export interface EssenceStat {
  /** 自定义显示名称，用于武器总览页面展示 */
  name?: string
  attribute: string | null
  secondary: string | null
  skill: string | null
}

export function getEmptyStat(): EssenceStat {
  return {
    attribute: null,
    secondary: null,
    skill: null,
  }
}

export function getGemTagName(gemId: string): string {
  const { essencesMap } = useStaticData()
  const essence = essencesMap.value.get(gemId)
  if (essence === undefined) {
    return gemId
  }
  return essence.tagName
}

export function getStatsForWeapon(weaponId: string): EssenceStat {
  const { weaponsMap } = useStaticData()
  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) {
    return getEmptyStat()
  }

  return {
    attribute: weapon.attributeStatId,
    secondary: weapon.secondaryStatId,
    skill: weapon.skillStatId,
  }
}

/** 自定义基质配置类型 */
export interface CustomStat {
  name?: string
  attribute: string | null
  secondary: string | null
  skill: string | null
  no_prompt_switch?: boolean
}

/**
 * 解析自定义基质的索引
 * @param weaponId 武器 ID（格式：custom_stat_N）
 * @returns 索引值，如果不是自定义基质则返回 null
 */
export function parseCustomStatIndex(weaponId: string): number | null {
  const match = weaponId.match(/^custom_stat_(\d+)$/)
  if (!match) return null
  return Number.parseInt(match[1]!, 10)
}

/**
 * 获取自定义基质的技能属性 ID
 * @param weaponId 武器 ID（格式：custom_stat_N）
 * @param customStats 自定义基质配置列表
 * @returns 技能属性 ID，如果不存在则返回 null
 */
export function getCustomStatSkillId(weaponId: string, customStats: CustomStat[]): string | null {
  const index = parseCustomStatIndex(weaponId)
  if (index === null) return null
  return customStats[index]?.skill || null
}

/**
 * 获取自定义基质的名称
 * @param weaponId 武器 ID（格式：custom_stat_N）
 * @param customStats 自定义基质配置列表
 * @returns 基质名称
 */
export function getCustomStatName(weaponId: string, customStats: CustomStat[]): string {
  const index = parseCustomStatIndex(weaponId)
  if (index === null) return '自定义基质'
  return customStats[index]?.name || `自定义基质 ${index + 1}`
}
