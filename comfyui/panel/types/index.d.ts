export type Blok = {
  id: string
  typ: string
  tytul: string
  stan: string
  value: number | null
  max: number | null
  start: number | null
  koniec: number | null
  wynik: string | null
}

export type Zadanie = {
  prompt_id: string
  start: number
  koniec?: number | null
  wynik?: string | null
  blad?: string | null
  bloki: Blok[]
}

export type Wpis = {
  prompt_id: string
  start: number
  koniec: number | null
  wynik: string | null
  blad: string | null
}

export type Migawka = {
  dziala: boolean
  teraz: number
  w_kolejce: number
  biezace: Zadanie | null
  ostatnie: Zadanie | null
  historia: Wpis[]
  vram_wolne: number | null
  vram_razem: number | null
  blad_polaczenia: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'muzyka-panel': { stan: Shaped<Migawka | null> }
  }
}
