import QRCode from 'qrcode'

/** What a sticker encodes: a normal link, so any phone camera can open it too. */
export function stickerUrl(workshopId: string, locationId: string) {
  return `${window.location.origin}/l/${workshopId}/${locationId}`
}

/** Parses a scanned text; returns the app path if it is one of our stickers. */
export function stickerPath(text: string): string | null {
  try {
    const url = new URL(text, window.location.origin)
    const m = url.pathname.match(/^\/l\/([0-9a-f-]{36})\/([0-9a-f-]{36})\/?$/i)
    return m ? `/l/${m[1]}/${m[2]}` : null
  } catch {
    return null
  }
}

export function qrSvg(text: string): Promise<string> {
  return QRCode.toString(text, { type: 'svg', margin: 0, errorCorrectionLevel: 'M' })
}
