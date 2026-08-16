import { describe, expect, it } from 'vitest'
import { computeCanvasSize, pickColumns } from '@/utils/matrixExport'

describe('pickColumns', () => {
  it('条目很少时每张卡各占一列，不留空位', () => {
    expect(pickColumns(1)).toBe(1)
    expect(pickColumns(2)).toBe(2)
    expect(pickColumns(3)).toBe(3)
  })

  it('按总数分档扩列', () => {
    expect(pickColumns(4)).toBe(3)
    expect(pickColumns(8)).toBe(3)
    expect(pickColumns(9)).toBe(4)
    expect(pickColumns(18)).toBe(4)
    expect(pickColumns(19)).toBe(5)
    expect(pickColumns(40)).toBe(5)
    expect(pickColumns(41)).toBe(6)
    expect(pickColumns(200)).toBe(6)
  })

  it('总数为 0 时也要返回合法列数，避免除零', () => {
    expect(pickColumns(0)).toBe(1)
  })
})

describe('computeCanvasSize', () => {
  it('宽度只由列数决定，与条目数无关', () => {
    const few = computeCanvasSize(3, 0, 3)
    const many = computeCanvasSize(30, 0, 3)
    expect(few.width).toBe(many.width)
  })

  it('行数按列数向上取整', () => {
    expect(computeCanvasSize(7, 5, 3)).toMatchObject({ weaponRows: 3, customRows: 2 })
  })

  it('没有自定义基质时不为该区留高度', () => {
    const withCustom = computeCanvasSize(6, 3, 3)
    const withoutCustom = computeCanvasSize(6, 0, 3)
    expect(withoutCustom.customRows).toBe(0)
    expect(withoutCustom.height).toBeLessThan(withCustom.height)
  })

  it('只有自定义基质时不为内置武器区留高度', () => {
    const onlyCustom = computeCanvasSize(0, 3, 3)
    const onlyWeapon = computeCanvasSize(3, 0, 3)
    expect(onlyCustom.weaponRows).toBe(0)
    // 两区各一行、区标题各一个，缺少区间距的情况下高度应当相等
    expect(onlyCustom.height).toBe(onlyWeapon.height)
  })

  it('两区都有时高度比单区多出一个区间距', () => {
    const both = computeCanvasSize(3, 3, 3)
    const onlyWeapon = computeCanvasSize(3, 0, 3)
    const oneSectionExtra = both.height - onlyWeapon.height
    // 多出的部分 = 区间距 + 区标题 + 一行卡片
    expect(oneSectionExtra).toBeGreaterThan(0)
    expect(both.weaponRows).toBe(1)
    expect(both.customRows).toBe(1)
  })

  it('列数为 0 时兜底成 1 列，不产生 Infinity', () => {
    const size = computeCanvasSize(3, 0, 0)
    expect(Number.isFinite(size.width)).toBe(true)
    expect(size.weaponRows).toBe(3)
  })
})
