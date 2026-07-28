declare module 'html2canvas' {
  interface Options {
    allowTaint?: boolean
    backgroundColor?: string | null
    canvas?: HTMLCanvasElement
    CORS?: boolean
    height?: number
    logging?: boolean
    onclone?: (document: Document) => void
    proxy?: string
    removeContainer?: boolean
    scale?: number
    scrollX?: number
    scrollY?: boolean
    useCORS?: boolean
    width?: number
    windowWidth?: number
    windowHeight?: number
    x?: number
    y?: number
  }

  function html2canvas(element: HTMLElement, options?: Options): Promise<HTMLCanvasElement>

  export default html2canvas
}
