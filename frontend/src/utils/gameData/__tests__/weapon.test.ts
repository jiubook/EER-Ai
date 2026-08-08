/**
 * 自定义基质标识工具测试。
 *
 * 这些函数是全前端唯一解析自定义基质 ID 的入口，一旦解析错位，
 * 界面上的名称、图标和等级都会张冠李戴，因此逐条锁定行为。
 */

import type { CustomStat } from '../weapon'

import { describe, expect, it } from 'vitest'
import {
  buildStatKey,
  createCustomStatId,
  CUSTOM_ID_PREFIX,
  fallbackCustomStatName,
  findCustomStat,
  isCustomStatId,
  toCustomStatId,
} from '../weapon'

function makeStat(id: string, name?: string): CustomStat {
  return { id, name, attribute: null, secondary: null, skill: null }
}

const STATS: CustomStat[] = [makeStat('aaa', '甲'), makeStat('bbb', '乙'), makeStat('ccc')]

describe('isCustomStatId', () => {
  it('识别新格式', () => {
    expect(isCustomStatId('custom:aaa')).toBe(true)
  })

  it('兼容识别迁移前的旧格式', () => {
    expect(isCustomStatId('custom_stat_0')).toBe(true)
  })

  it('普通武器与空值返回 false', () => {
    expect(isCustomStatId('wpn_001')).toBe(false)
    expect(isCustomStatId(null)).toBe(false)
    expect(isCustomStatId(undefined)).toBe(false)
    expect(isCustomStatId('')).toBe(false)
  })
})

describe('findCustomStat', () => {
  it('按 ID 命中，与所在下标无关', () => {
    const found = findCustomStat('custom:bbb', STATS)
    expect(found?.stat.name).toBe('乙')
    expect(found?.index).toBe(1)
  })

  it('删除前面的条目后，同一个 ID 仍指向同一条记录', () => {
    // 这正是稳定 ID 要解决的问题：下标变了，引用不该跟着错位
    const afterDelete = STATS.slice(1)
    const found = findCustomStat('custom:bbb', afterDelete)
    expect(found?.stat.name).toBe('乙')
    expect(found?.index).toBe(0)
  })

  it('ID 不存在时返回 null', () => {
    expect(findCustomStat('custom:missing', STATS)).toBeNull()
  })

  it('旧格式按下标兜底解析', () => {
    expect(findCustomStat('custom_stat_2', STATS)?.stat.id).toBe('ccc')
  })

  it('旧格式下标越界返回 null', () => {
    expect(findCustomStat('custom_stat_9', STATS)).toBeNull()
  })

  it('旧格式后缀非数字返回 null', () => {
    expect(findCustomStat('custom_stat_abc', STATS)).toBeNull()
  })

  it('普通武器 ID 与空值返回 null', () => {
    expect(findCustomStat('wpn_001', STATS)).toBeNull()
    expect(findCustomStat(null, STATS)).toBeNull()
  })
})

describe('toCustomStatId', () => {
  it('拼接前缀', () => {
    expect(toCustomStatId({ id: 'xyz' })).toBe(`${CUSTOM_ID_PREFIX}xyz`)
  })

  it('与 findCustomStat 互为逆运算', () => {
    for (const stat of STATS) {
      expect(findCustomStat(toCustomStatId(stat), STATS)?.stat.id).toBe(stat.id)
    }
  })
})

describe('createCustomStatId', () => {
  it('生成非空且互不相同的 ID', () => {
    const ids = new Set(Array.from({ length: 50 }, () => createCustomStatId()))
    expect(ids.size).toBe(50)
    expect([...ids].every((id) => id.length > 0)).toBe(true)
  })

  it('生成的 ID 可被 findCustomStat 正确检索', () => {
    const stat = makeStat(createCustomStatId(), '新建')
    expect(findCustomStat(toCustomStatId(stat), [stat])?.stat.name).toBe('新建')
  })
})

describe('buildStatKey', () => {
  it('内置武器与自定义基质的同类字段生成相同键', () => {
    // 连线层用该键把自定义基质与内置武器互相匹配，格式必须一致
    expect(buildStatKey('gem_attr', 'gem_sec', 'gem_skill')).toBe('gem_attr|gem_sec|gem_skill')
  })

  it('空属性用 null 占位，仍能与内置武器的空字段匹配', () => {
    expect(buildStatKey(null, 'gem_sec', null)).toBe('null|gem_sec|null')
  })

  it('不同顺序/不同值生成不同键', () => {
    expect(buildStatKey('a', 'b', 'c')).not.toBe(buildStatKey('a', 'c', 'b'))
  })
})

describe('fallbackCustomStatName', () => {
  it('按 1 起编号', () => {
    expect(fallbackCustomStatName(0)).toBe('自定义基质 1')
    expect(fallbackCustomStatName(4)).toBe('自定义基质 5')
  })
})
