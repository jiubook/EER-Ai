/**
 * 宝藏基质导出图的 Canvas 绘制模块。
 *
 * 这里只负责「把一组卡片画成一张 PNG」，不感知任何应用状态：
 * 调用方把 profile、静态数据、主题色整理成普通对象传进来。
 * 这样布局计算能在 node 环境的单测里直接跑，无需 DOM。
 */

import Color from 'color'

/** 导出图里的一张卡片 */
export interface ExportCard {
  /** 'weapon' 画武器 icon + 基质小图；'custom' 只画放大的基质图 */
  kind: 'weapon' | 'custom'
  name: string
  /** 武器 icon 地址；自定义基质没有武器图，传 null */
  iconUrl: string | null
  /** 基质底板地址 */
  essenceBgUrl: string
  /** 技能属性图标地址 */
  skillIconUrl: string | null
  /** 底部色条颜色：内置武器用稀有度色，自定义基质用橙色 */
  tierColor: string
  levels: readonly [number, number, number]
  maxed: boolean
  /** 扫描到的基质枚数；缺省或非正数时不画角标 */
  badgeCount?: number
  /** 三词条中文名，如 ["攻击", "终结技充能效率", "巧技"] */
  traitNames?: string[]
}

/**
 * 绘制用的主题色。
 *
 * canvas 读不到 `--v-theme-*` 这类 CSS 变量，颜色必须由调用方从
 * Vuetify 的 `useTheme()` 里取出来显式传入。
 */
export interface ExportTheme {
  primary: string
  onPrimary: string
  background: string
  surface: string
  onSurface: string
}

export interface MatrixExportInput {
  /** 内置武器卡，调用方已排好序 */
  weapons: readonly ExportCard[]
  /** 自定义基质卡，永远画在最下方 */
  customs: readonly ExportCard[]
  title: string
  subtitle: string
  theme: ExportTheme
  /** 像素倍率，默认 2；超出画布上限时内部自动降级 */
  scale?: number
  /** 网格列数，不传则按卡片总数自适应 */
  columns?: number
}

export interface MatrixExportResult {
  blob: Blob
  /** 预览用的 object URL，调用方负责 revoke */
  objectUrl: string
  /** CSS 像素尺寸（非设备像素） */
  width: number
  height: number
  /** 实际生效的倍率，可能因画布上限被降级 */
  scale: number
  /** 加载失败、已用占位图代替的图片数量 */
  missingImages: number
}

/** 各词条的方格数，与 useWeaponStats 的 AFFIX_MAX_LEVEL 保持一致 */
const AFFIX_PIP_COUNT = [6, 6, 3] as const

/**
 * 词条槽位配色。
 *
 * 基础属性跟随主题 primary，另外两个沿用 treasure-matrix.vue 里
 * $attr-teal / $attr-indigo 的字面值，保证导出图与页面观感一致。
 */
const ATTR_TEAL = '#48a9a6'
const ATTR_INDIGO = '#5c6bc0'

/** 满级彩虹环的渐变色，取自 WeaponOverview.vue 的 .rainbow-border */
const RAINBOW_STOPS = [
  '#ffffff',
  '#ff4ada',
  '#ff4e4e',
  '#ff9832',
  '#ffff00',
  '#00ff00',
  '#00ffff',
  '#79a0fd',
  '#d46eff',
  '#ff8df0',
  '#ffffff',
] as const

/** 自定义基质的主题橙，与 CustomStatIcon.vue 一致 */
const CUSTOM_ORANGE = '#ff7100'

// --- 布局常量（CSS 像素）---
const PAGE_PAD = 24
const GAP = 14
const SECTION_GAP = 22
const HEADER_H = 62
const SECTION_HEAD_H = 30
const CARD_W = 260
const CARD_H = 132
const CARD_R = 3
const CARD_PAD = 12
const NAME_H = 22
const ICON = 56
const MATRIX_ICON = 56
const PIP_W = 8
const PIP_H = 12
const PIP_GAP = 3
const PIP_ROW_GAP = 21
const BADGE_R = 11
const TRAIT_FONTSIZE = 12

/** 画布单边的设备像素上限，取远低于 Chromium 16384 的保守值 */
const MAX_DEVICE_PX = 8192

const FONT_STACK = '"HarmonyOS Sans SC", sans-serif'

/**
 * 按卡片总数选择网格列数。
 *
 * 两个区共用同一列数，网格才对得齐。
 */
export function pickColumns(cardCount: number): number {
  if (cardCount <= 3) return Math.max(1, cardCount)
  if (cardCount <= 8) return 3
  if (cardCount <= 18) return 4
  if (cardCount <= 40) return 5
  return 6
}

/**
 * 计算画布尺寸与两个区各自的行数。
 *
 * 任一区为空时，该区连同区标题都不占高度。
 */
export function computeCanvasSize(
  weaponCount: number,
  customCount: number,
  columns: number,
): { width: number; height: number; weaponRows: number; customRows: number } {
  const cols = Math.max(1, columns)
  const weaponRows = Math.ceil(weaponCount / cols)
  const customRows = Math.ceil(customCount / cols)

  const width = PAGE_PAD * 2 + cols * CARD_W + (cols - 1) * GAP

  let height = PAGE_PAD + HEADER_H
  if (weaponRows > 0) {
    height += SECTION_HEAD_H + weaponRows * (CARD_H + GAP) - GAP
  }
  if (customRows > 0) {
    if (weaponRows > 0) height += SECTION_GAP
    height += SECTION_HEAD_H + customRows * (CARD_H + GAP) - GAP
  }
  height += PAGE_PAD

  return { width, height, weaponRows, customRows }
}

/**
 * 图片缓存：只缓存加载成功的，失败的下次重试
 * （浏览器自己会缓存 404，重试成本很低）。
 */
const imageCache = new Map<string, HTMLImageElement>()

/** 加载单张图片；失败时返回 null，由调用方画占位图 */
async function loadImage(url: string): Promise<HTMLImageElement | null> {
  const cached = imageCache.get(url)
  if (cached) return cached

  const image = new Image()
  image.src = url
  try {
    // decode() 在 404 或解码失败时 reject，这里统一降级为 null
    await image.decode()
  } catch {
    return null
  }
  imageCache.set(url, image)
  return image
}

/** 并发预加载所有卡片用到的图片，返回 url -> 图片（失败为 null）的映射 */
async function preloadImages(
  cards: readonly ExportCard[],
): Promise<Map<string, HTMLImageElement | null>> {
  const urls = new Set<string>()
  for (const card of cards) {
    if (card.iconUrl) urls.add(card.iconUrl)
    if (card.essenceBgUrl) urls.add(card.essenceBgUrl)
    if (card.skillIconUrl) urls.add(card.skillIconUrl)
  }

  const entries = await Promise.all(
    [...urls].map(async (url) => [url, await loadImage(url)] as const),
  )
  return new Map(entries)
}

/** 把 canvas 转成 PNG Blob；toBlob 是回调式的，这里包一层 Promise */
function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('画布导出失败'))
    }, 'image/png')
  })
}

/** 以 rgba 形式取主题色的透明度变体 */
function withAlpha(color: string, alpha: number): string {
  return Color(color).alpha(alpha).string()
}

/**
 * 把主题色统一规范成 canvas 一定认得的 rgb 字符串。
 *
 * canvas 对无效的 fillStyle 是静默忽略的——一个 undefined 会让文字直接消失，
 * 而不是报错。这里先过一遍 color 包（它把无效值兜底成黑色），
 * 让"取色取错了"至少表现为颜色不对，而不是整块内容不翼而飞。
 */
function normalizeTheme(theme: ExportTheme): ExportTheme {
  const toRgb = (color: string) => Color(color).string()
  return {
    primary: toRgb(theme.primary),
    onPrimary: toRgb(theme.onPrimary),
    background: toRgb(theme.background),
    surface: toRgb(theme.surface),
    onSurface: toRgb(theme.onSurface),
  }
}

/**
 * 把文字压进指定宽度：先按比例缩字号，到下限仍超宽则尾部截断加省略号。
 *
 * 思路与 utils/autoFontSizing.ts 一致，只是把 DOM 测量换成 measureText。
 * 返回前会把 ctx.font 留在最终字号上，调用方紧接着 fillText 即可。
 */
function fitText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxFontSize: number,
  minFontSize: number,
  weight = 700,
): string {
  ctx.font = `${weight} ${maxFontSize}px ${FONT_STACK}`
  const fullWidth = ctx.measureText(text).width
  if (fullWidth <= maxWidth) return text

  const scaled = Math.max((maxFontSize * maxWidth) / fullWidth, minFontSize)
  ctx.font = `${weight} ${scaled}px ${FONT_STACK}`
  if (ctx.measureText(text).width <= maxWidth) return text

  // 缩到下限仍放不下，只能截断
  let truncated = text
  while (truncated.length > 1 && ctx.measureText(`${truncated}…`).width > maxWidth) {
    truncated = truncated.slice(0, -1)
  }
  return `${truncated}…`
}

/** 清掉阴影设置。canvas 的 shadow 是全局状态，画完必须复位，否则后续绘制全带影子 */
function clearShadow(ctx: CanvasRenderingContext2D): void {
  ctx.shadowColor = 'transparent'
  ctx.shadowBlur = 0
  ctx.shadowOffsetX = 0
  ctx.shadowOffsetY = 0
}

/** 按 object-fit: cover 的规则把图片画进目标矩形 */
function drawImageCover(
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight)
  const drawW = image.naturalWidth * scale
  const drawH = image.naturalHeight * scale
  ctx.drawImage(image, x + (width - drawW) / 2, y + (height - drawH) / 2, drawW, drawH)
}

/** 图片缺失时的占位块 */
function drawImagePlaceholder(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  x: number,
  y: number,
  size: number,
): void {
  ctx.fillStyle = withAlpha(theme.onSurface, 0.08)
  ctx.beginPath()
  ctx.roundRect(x, y, size, size, 3)
  ctx.fill()

  ctx.fillStyle = withAlpha(theme.onSurface, 0.35)
  ctx.font = `700 ${Math.round(size * 0.32)}px ${FONT_STACK}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('?', x + size / 2, y + size / 2)
}

/**
 * 画武器 icon：图片 + 底部稀有度渐变 + 底部色条。
 *
 * 对应 ItemIcon.vue 的三层结构，但不画 icon 内嵌名称——
 * 56px 见方塞中文名不可读，名称在卡片里有独立一行。
 */
function drawWeaponIcon(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  image: HTMLImageElement | null,
  card: ExportCard,
  x: number,
  y: number,
  size: number,
): void {
  if (!image) {
    drawImagePlaceholder(ctx, theme, x, y, size)
    return
  }

  ctx.save()
  ctx.beginPath()
  ctx.roundRect(x, y, size, size, 3)
  ctx.clip()

  drawImageCover(ctx, image, x, y, size, size)

  // 底部 70%→100% 的稀有度色渐变
  const gradient = ctx.createLinearGradient(x, y, x, y + size)
  gradient.addColorStop(0.7, withAlpha(card.tierColor, 0))
  gradient.addColorStop(1, withAlpha(card.tierColor, 0.3))
  ctx.fillStyle = gradient
  ctx.fillRect(x, y, size, size)

  // 底部 4% 高的稀有度色条
  const barHeight = Math.max(2, size * 0.04)
  ctx.fillStyle = card.tierColor
  ctx.fillRect(x, y + size - barHeight, size, barHeight)

  ctx.restore()
}

/**
 * 画基质图：底板 + 技能图标 + 橙色渐变 + 底部橙条 + 橙色描边。
 *
 * 对应 CustomStatIcon.vue 的层叠结构，技能图标沿用 translate(5%, -5%) 的偏移。
 */
function drawEssenceIcon(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  bgImage: HTMLImageElement | null,
  skillImage: HTMLImageElement | null,
  x: number,
  y: number,
  size: number,
): void {
  if (!bgImage && !skillImage) {
    drawImagePlaceholder(ctx, theme, x, y, size)
    return
  }

  ctx.save()
  ctx.beginPath()
  ctx.roundRect(x, y, size, size, 3)
  ctx.clip()

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(x, y, size, size)
  if (bgImage) drawImageCover(ctx, bgImage, x, y, size, size)
  if (skillImage) {
    drawImageCover(ctx, skillImage, x + size * 0.05, y - size * 0.05, size, size)
  }

  const gradient = ctx.createLinearGradient(x, y, x, y + size)
  gradient.addColorStop(0.7, withAlpha(CUSTOM_ORANGE, 0))
  gradient.addColorStop(1, withAlpha(CUSTOM_ORANGE, 0.3))
  ctx.fillStyle = gradient
  ctx.fillRect(x, y, size, size)

  const barHeight = Math.max(2, size * 0.04)
  ctx.fillStyle = CUSTOM_ORANGE
  ctx.fillRect(x, y + size - barHeight, size, barHeight)

  ctx.restore()

  ctx.strokeStyle = withAlpha(CUSTOM_ORANGE, 0.5)
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.roundRect(x + 1, y + 1, size - 2, size - 2, 3)
  ctx.stroke()
}

/** 画一行方格能量条，对应 treasure-matrix.vue 的 .attr-pips */
function drawPipRow(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  level: number,
  pipCount: number,
  activeColor: string,
  x: number,
  y: number,
): void {
  for (let index = 0; index < pipCount; index++) {
    const pipX = x + index * (PIP_W + PIP_GAP)
    const active = index < level

    if (active) {
      ctx.shadowColor = withAlpha(activeColor, 0.32)
      ctx.shadowBlur = 7
      ctx.shadowOffsetY = 2
      ctx.fillStyle = activeColor
    } else {
      ctx.fillStyle = withAlpha(theme.onSurface, 0.12)
    }

    ctx.beginPath()
    ctx.roundRect(pipX, y, PIP_W, PIP_H, 2)
    ctx.fill()
    clearShadow(ctx)
  }

  ctx.fillStyle = withAlpha(theme.onSurface, 0.68)
  ctx.font = `800 10px ${FONT_STACK}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(`${level}/${pipCount}`, x + pipCount * (PIP_W + PIP_GAP) + 4, y + PIP_H / 2)
}

/** 满级卡片的彩虹外框，取 WeaponOverview.vue 彩虹环渐变的一帧 */
function drawRainbowBorder(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  // 45° 方向：从左下到右上
  const gradient = ctx.createLinearGradient(x, y + height, x + width, y)
  for (const [index, color] of RAINBOW_STOPS.entries()) {
    gradient.addColorStop(index / (RAINBOW_STOPS.length - 1), color)
  }

  ctx.strokeStyle = gradient
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.roundRect(x + 1, y + 1, width - 2, height - 2, CARD_R)
  ctx.stroke()
}

/** 扫描数量角标，对应设置页 v-badge 的右上角圆形数字 */
function drawBadge(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  count: number,
  centerX: number,
  centerY: number,
): void {
  ctx.fillStyle = theme.primary
  ctx.beginPath()
  ctx.arc(centerX, centerY, BADGE_R, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = theme.onPrimary
  ctx.font = `700 11px ${FONT_STACK}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(count > 99 ? '99+' : String(count), centerX, centerY)
}

/**
 * 处理词条名称：去掉"提升"后缀以缩短显示长度。
 *
 * "攻击力提升" → "攻击"
 * "终结技充能效率提升" → "终结技充能效率"
 * "巧技" → "巧技"（无"提升"则保持不变）
 */
function shortenTraitName(name: string): string {
  if (name.endsWith('提升')) {
    return name.slice(0, -2)
  }
  return name
}

/** 画一整张卡片 */
function drawCard(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  card: ExportCard,
  images: Map<string, HTMLImageElement | null>,
  x: number,
  y: number,
): void {
  ctx.fillStyle = theme.surface
  ctx.beginPath()
  ctx.roundRect(x, y, CARD_W, CARD_H, CARD_R)
  ctx.fill()
  ctx.strokeStyle = withAlpha(theme.onSurface, 0.12)
  ctx.lineWidth = 1
  ctx.stroke()

  // 名称行
  const nameMaxWidth = CARD_W - CARD_PAD * 2
  const nameText = fitText(ctx, card.name, nameMaxWidth, 14, 10)
  ctx.fillStyle = theme.onSurface
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(nameText, x + CARD_W / 2, y + CARD_PAD + NAME_H / 2)

  const bodyY = y + CARD_PAD + NAME_H + 4
  const iconImage = card.iconUrl ? (images.get(card.iconUrl) ?? null) : null
  const bgImage = card.essenceBgUrl ? (images.get(card.essenceBgUrl) ?? null) : null
  const skillImage = card.skillIconUrl ? (images.get(card.skillIconUrl) ?? null) : null

  let pipX: number
  if (card.kind === 'weapon') {
    const iconX = x + CARD_PAD
    drawWeaponIcon(ctx, theme, iconImage, card, iconX, bodyY, ICON)

    const essenceX = iconX + ICON + 10
    const essenceY = bodyY + (ICON - MATRIX_ICON) / 2
    drawEssenceIcon(ctx, theme, bgImage, skillImage, essenceX, essenceY, MATRIX_ICON)
    pipX = essenceX + MATRIX_ICON + 12

    if (card.badgeCount && card.badgeCount > 0) {
      drawBadge(ctx, theme, card.badgeCount, iconX + ICON, bodyY)
    }
  } else {
    // 自定义基质没有武器图，基质图放大占据 icon 的位置
    const essenceX = x + CARD_PAD
    drawEssenceIcon(ctx, theme, bgImage, skillImage, essenceX, bodyY, ICON)
    pipX = essenceX + ICON + 12
  }

  // 三行方格能量条
  const pipColors = [theme.primary, ATTR_TEAL, ATTR_INDIGO]
  for (let slot = 0; slot < 3; slot++) {
    drawPipRow(
      ctx,
      theme,
      card.levels[slot] ?? 0,
      AFFIX_PIP_COUNT[slot]!,
      pipColors[slot]!,
      pipX,
      bodyY + slot * PIP_ROW_GAP,
    )
  }

  // 底部词条名
  if (card.traitNames && card.traitNames.length > 0) {
    const traitText = card.traitNames.map((name) => shortenTraitName(name)).join('·')
    const traitMaxWidth = CARD_W - CARD_PAD * 2
    const traitY = y + CARD_H - CARD_PAD - 4
    ctx.fillStyle = withAlpha(theme.onSurface, 0.55)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    const fittedText = fitText(ctx, traitText, traitMaxWidth, TRAIT_FONTSIZE, 10, 400)
    ctx.fillText(fittedText, x + CARD_W / 2, traitY)
  }

  if (card.maxed) drawRainbowBorder(ctx, x, y, CARD_W, CARD_H)
}

/** 画区标题，返回下一个可用的 y 坐标 */
function drawSectionHeader(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  text: string,
  x: number,
  y: number,
  width: number,
): number {
  ctx.fillStyle = withAlpha(theme.onSurface, 0.62)
  ctx.font = `700 14px ${FONT_STACK}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, x, y + SECTION_HEAD_H / 2)

  ctx.strokeStyle = withAlpha(theme.onSurface, 0.12)
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(x + ctx.measureText(text).width + 12, y + SECTION_HEAD_H / 2)
  ctx.lineTo(x + width, y + SECTION_HEAD_H / 2)
  ctx.stroke()

  return y + SECTION_HEAD_H
}

/** 画一个网格区，返回下一个可用的 y 坐标 */
function drawGrid(
  ctx: CanvasRenderingContext2D,
  theme: ExportTheme,
  cards: readonly ExportCard[],
  images: Map<string, HTMLImageElement | null>,
  columns: number,
  y: number,
): number {
  for (const [index, card] of cards.entries()) {
    const row = Math.floor(index / columns)
    const column = index % columns
    drawCard(ctx, theme, card, images, PAGE_PAD + column * (CARD_W + GAP), y + row * (CARD_H + GAP))
  }

  const rows = Math.ceil(cards.length / columns)
  return y + rows * (CARD_H + GAP) - GAP
}

/**
 * 把宝藏基质卡片渲染成一张 PNG。
 *
 * @param input 卡片数据、标题与主题色。
 * @returns PNG Blob、预览用 object URL 及实际尺寸。
 * @throws 卡片为空、或画布导出失败时抛出。
 */
export async function renderMatrixExport(input: MatrixExportInput): Promise<MatrixExportResult> {
  const { weapons, customs } = input
  const theme = normalizeTheme(input.theme)
  const allCards = [...weapons, ...customs]
  if (allCards.length === 0) {
    throw new Error('没有可导出的条目')
  }

  const columns = input.columns ?? pickColumns(allCards.length)
  const { width, height } = computeCanvasSize(weapons.length, customs.length, columns)

  const images = await preloadImages(allCards)
  let missingImages = 0
  for (const image of images.values()) {
    if (!image) missingImages++
  }

  // 固定倍率而非跟随 devicePixelRatio：同一份数据在任何机器上都应产出同样的图
  const requestedScale = input.scale ?? 2
  const scale = Math.max(1, Math.min(requestedScale, MAX_DEVICE_PX / Math.max(width, height)))

  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法创建画布上下文')

  // 缩放一次之后，下面所有布局数学都按 CSS 像素来写
  ctx.scale(scale, scale)

  ctx.fillStyle = theme.background
  ctx.fillRect(0, 0, width, height)

  // 页头
  ctx.fillStyle = theme.onSurface
  ctx.font = `700 18px ${FONT_STACK}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(input.title, PAGE_PAD, PAGE_PAD + 16)
  ctx.fillStyle = withAlpha(theme.onSurface, 0.55)
  ctx.font = `400 12px ${FONT_STACK}`
  ctx.fillText(input.subtitle, PAGE_PAD, PAGE_PAD + 40)

  const gridWidth = width - PAGE_PAD * 2
  let cursorY = PAGE_PAD + HEADER_H

  if (weapons.length > 0) {
    cursorY = drawSectionHeader(
      ctx,
      theme,
      `内置武器 (${weapons.length})`,
      PAGE_PAD,
      cursorY,
      gridWidth,
    )
    cursorY = drawGrid(ctx, theme, weapons, images, columns, cursorY)
  }

  if (customs.length > 0) {
    if (weapons.length > 0) cursorY += SECTION_GAP
    cursorY = drawSectionHeader(
      ctx,
      theme,
      `自定义基质 (${customs.length})`,
      PAGE_PAD,
      cursorY,
      gridWidth,
    )
    drawGrid(ctx, theme, customs, images, columns, cursorY)
  }

  const blob = await canvasToBlob(canvas)
  return {
    blob,
    objectUrl: URL.createObjectURL(blob),
    width,
    height,
    scale,
    missingImages,
  }
}
