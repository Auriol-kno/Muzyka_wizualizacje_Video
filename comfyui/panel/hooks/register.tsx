import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Blok, Migawka, Zadanie } from '../types'

// Panel „Muzyka Graficznie – przepływ pracy”: bloki workflow ComfyUI na żywo
// (który liczy, postęp, czas, wynik kontroli). Dane: GET /mg/stan (węzły
// comfyui/wezly) + /system_stats. Odświeżanie co 2 s, tylko gdy panel jest widoczny.
const PANE = 'muzyka-przeplyw'
const TYTUL = 'Muzyka Graficznie – przepływ pracy'
const URL = 'http://127.0.0.1:8188'

const stan = atom({ plugin: 'muzyka-panel', key: 'stan' } as const, null, { shape: 'migawka-1' })

let zegar: { cancel: () => void } | null = null

const czas = (s: number) => {
  const m = Math.floor(s / 60)
  const godz = Math.floor(m / 60)
  return godz ? `${godz} h ${m % 60} min` : m ? `${m} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`
}

const pasek = (v: number, max: number, szer = 20) => {
  const p = Math.max(0, Math.min(1, v / max))
  const n = Math.round(p * szer)
  return '█'.repeat(n) + '░'.repeat(szer - n) + ` ${v}/${max} (${Math.round(p * 100)}%)`
}

const KOLOR: Record<string, string> = {
  liczy: 'warning',
  gotowe: 'success',
  'z pamięci': 'success',
  błąd: 'error',
  czeka: 'inactive',
}
const ZNAK: Record<string, string> = {
  liczy: '▶',
  gotowe: '✓',
  'z pamięci': '✓',
  błąd: '✗',
  czeka: '○',
}

async function pobierz($: any): Promise<Migawka> {
  const pusta: Migawka = {
    dziala: false, teraz: Date.now() / 1000, w_kolejce: 0, biezace: null, ostatnie: null,
    historia: [], vram_wolne: null, vram_razem: null, blad_polaczenia: null,
  }
  try {
    const r = await $.http.fetch(`${URL}/mg/stan`)
    if (!r.ok) return { ...pusta, dziala: true, blad_polaczenia: `/mg/stan: HTTP ${r.status} (zrestartuj ComfyUI)` }
    const d = JSON.parse(r.text)
    let vw: number | null = null
    let vr: number | null = null
    try {
      const s = await $.http.fetch(`${URL}/system_stats`)
      const g = JSON.parse(s.text).devices?.[0]
      if (g) { vw = g.vram_free / 2 ** 30; vr = g.vram_total / 2 ** 30 }
    } catch { /* bez VRAM */ }
    return { ...pusta, ...d, dziala: true, vram_wolne: vw, vram_razem: vr }
  } catch (err) {
    return { ...pusta, blad_polaczenia: 'ComfyUI nie odpowiada – python -m comfyui.uruchom' }
  }
}

async function odswiez($: any) {
  const m = await pobierz($)
  await update($, stan, () => m)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'przeplyw', description: 'Panel: przepływ pracy ComfyUI (Muzyka Graficznie)' })
    void $.ui.open({ id: PANE, title: TYTUL })
    zegar?.cancel()
    zegar = $.clock.every(2000, async () => {
      const panes = await $.ui.panes()
      if (panes.some((p: any) => p.id === PANE && p.isShown)) await odswiez($)
    })
    void odswiez($)
    return next(e)
  })

  on('command.run', { command: 'przeplyw' }, async $ => {
    await $.ui.open({ id: PANE, title: TYTUL })
    await odswiez($)
    return { text: 'Panel przepływu pracy otwarty.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const m = await read($, stan)
    if (!m) return <Text dimColor>Łączę z ComfyUI…</Text>

    const blok = (b: Blok, teraz: number) => {
      const s = b.stan
      const trwa = b.start ? czas((b.koniec ?? (s === 'liczy' ? teraz : b.start)) - b.start) : ''
      return (
        <Box flexDirection="column" borderStyle="round" borderColor={KOLOR[s] ?? 'inactive'} paddingX={1}>
          <Text bold={s === 'liczy'} dimColor={s === 'czeka'}>
            {ZNAK[s] ?? '○'} {b.tytul}
          </Text>
          <Text dimColor>
            {s}{trwa ? ` · ${trwa}` : ''}{b.typ !== b.tytul ? ` · ${b.typ}` : ''}
          </Text>
          {s === 'liczy' && b.max ? <Text color="warning">{pasek(b.value ?? 0, b.max)}</Text> : null}
          {b.wynik ? <Text dimColor>{b.wynik.split('\n')[0].slice(0, 120)}</Text> : null}
        </Box>
      )
    }

    const zadanie = (z: Zadanie, naglowek: string) => (
      <Box flexDirection="column" gap={0}>
        <Text bold>{naglowek}</Text>
        {z.bloki.map((b, i) => (
          <Box flexDirection="column">
            {i > 0 ? <Text dimColor>   ↓</Text> : null}
            {blok(b, m.teraz)}
          </Box>
        ))}
        {z.blad ? <Text color="error">{z.blad}</Text> : null}
      </Box>
    )

    const vram = m.vram_razem ? `VRAM wolne ${m.vram_wolne!.toFixed(1)} / ${m.vram_razem.toFixed(1)} GB` : ''
    return (
      <Box flexDirection="column" gap={1}>
        <Text dimColor>
          {m.dziala ? '● ComfyUI 127.0.0.1:8188' : '○ ComfyUI wyłączony'}
          {vram ? ` · ${vram}` : ''} · w kolejce {m.w_kolejce}
        </Text>
        {m.blad_polaczenia ? <Text color="error">{m.blad_polaczenia}</Text> : null}
        {m.biezace
          ? zadanie(m.biezace, `▶ Teraz liczy · ${czas(m.teraz - m.biezace.start)}`)
          : m.dziala ? <Text>Bezczynny – nic się nie liczy.</Text> : null}
        {!m.biezace && m.ostatnie
          ? zadanie(m.ostatnie, `Ostatnie zadanie: ${m.ostatnie.wynik ?? ''}` +
              (m.ostatnie.koniec ? ` · ${czas(m.ostatnie.koniec - m.ostatnie.start)}` : ''))
          : null}
        {m.historia.length > 0 ? (
          <Box flexDirection="column">
            <Text bold>Historia</Text>
            {m.historia.slice(0, 6).map(wpis => (
              <Text dimColor={wpis.wynik === 'ok'} color={wpis.wynik === 'ok' ? undefined : 'error'}>
                {wpis.wynik === 'ok' ? '✓' : '✗'} {new Date(wpis.start * 1000).toLocaleTimeString('pl-PL')}
                {wpis.koniec ? ` · ${czas(wpis.koniec - wpis.start)}` : ''}{wpis.blad ? ` · ${wpis.blad.slice(0, 80)}` : ''}
              </Text>
            ))}
          </Box>
        ) : null}
      </Box>
    )
  })
}
