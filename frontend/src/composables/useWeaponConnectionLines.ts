/**
 * 武器连线系统组合式函数。
 *
 * 管理武器之间的属性连线显示。
 */

import { onUnmounted, ref } from 'vue'

export interface ConnectionLine {
  style: {
    left: string
    top: string
    width: string
    transform: string
    opacity: number
  }
}

export function useWeaponConnectionLines() {
  /** 容器引用 */
  const containerRef = ref<HTMLElement | null>(null)

  /** 当前悬停的武器 ID */
  const hoveredWeaponId = ref<string | null>(null)

  /** 连线数据 */
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
  function updateConnectionLines(sameStatWeapons: string[]) {
    if (!hoveredWeaponId.value) {
      connectionLines.value = []
      return
    }

    const startPos = getWeaponElementPosition(hoveredWeaponId.value)
    if (!startPos) {
      connectionLines.value = []
      return
    }

    const newLines: ConnectionLine[] = []

    for (const targetId of sameStatWeapons) {
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
  function handleWeaponMouseEnter(weaponId: string, sameStatWeapons: string[]) {
    hoveredWeaponId.value = weaponId
    updateConnectionLines(sameStatWeapons)
  }

  /** 鼠标离开武器 */
  function handleWeaponMouseLeave() {
    hoveredWeaponId.value = null
    connectionLines.value = []
  }

  // 监听窗口大小变化，更新连线位置
  let resizeHandler: (() => void) | null = null

  function setupResizeListener(getSameStatWeapons: () => string[]) {
    resizeHandler = () => {
      if (hoveredWeaponId.value) {
        updateConnectionLines(getSameStatWeapons())
      }
    }
    window.addEventListener('resize', resizeHandler)
  }

  function cleanupResizeListener() {
    if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler)
      resizeHandler = null
    }
  }

  onUnmounted(() => {
    cleanupResizeListener()
    connectionLines.value = []
  })

  return {
    // 状态
    containerRef,
    hoveredWeaponId,
    connectionLines,

    // 方法
    updateConnectionLines,
    handleWeaponMouseEnter,
    handleWeaponMouseLeave,
    setupResizeListener,
    cleanupResizeListener,
  }
}
