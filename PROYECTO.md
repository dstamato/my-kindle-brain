# Cerebro Kindle — Documentación del proyecto

**Archivo principal:** `/Users/diegostamato/Desktop/my-kindle-brain/kindle_hibrido.html`  
**Arquitectura:** single-file HTML + CSS + JS (`<script type="module">`), sin dependencias externas.  
**Propósito:** buscador personal de subrayados de Kindle/Boox con BM25, biblioteca visual y compartir en X.

---

## Stack técnico

- **Búsqueda:** BM25 (implementación propia, sin librerías)
- **Fuentes:** Google Fonts — Playfair Display (serif, textos) + DM Sans (sans, UI)
- **Persistencia:** IndexedDB (`kindleBrain` DB, store `index`, key `'current'`)
- **Covers:** Open Library API (`search.json?title=...&author=...`) con validación 60% word-overlap
- **Compartir:** Canvas API (1200×628px quote card) → clipboard → X intent URL
- **Font size:** localStorage (`clipFontSize`, `hlFontSize`)
- **Libros ocultos:** localStorage (`hiddenBooks`)

---

## Paleta de colores (CSS variables)

```css
--ink:     #0a0a0a   /* negro principal */
--ink-2:   #333333   /* texto secundario */
--ink-3:   #888888   /* texto terciario, placeholders */
--paper:   #ffffff   /* fondo principal */
--paper-2: #f5f5f5   /* fondo sidebar, inputs */
--paper-3: #e2e2e2   /* bordes, separadores */
--accent:  #0a0a0a   /* igual a ink */
--line:    rgba(0,0,0,0.08)
```

---

## Layout (Readwise-style sidebar)

```
#screen-app (display:flex)
├── #sidebar (250px, sticky, height:100vh)
│   ├── .sidebar-brand
│   ├── .sidebar-search → #search-input + #btn-search + #stats-bar
│   ├── QUICK LINKS → #nav-search, #nav-library, #btn-add-source
│   └── LIBROS → #sb-all + #sidebar-book-list
└── #main-content (flex:1)
    ├── #search-content
    │   ├── .main-header → .main-title + #result-count + #hl-font-slider
    │   └── #results
    └── #screen-library (display:none por CSS)
        ├── .main-header → .main-title + #lib-search + #retry-covers-btn
        └── #lib-content

#screen-book-detail (fuera de #screen-app, mostrado via show())
```

**Importante:** `show('screen-app')` usa `display:flex` (no `block`). `#screen-library` tiene `display:none` en CSS por defecto.

---

## Variables de estado (módulo JS)

```javascript
let clippings = []         // clips para BM25 (deduplicados, max 1200 chars)
let allClippings = []      // todos los clips sin cap (para browse y Biblioteca)
let bm25Index = null       // índice BM25 { tf, idf, dl, avgdl, N }
let currentResults = []    // resultados de la última búsqueda BM25
let currentPage = 1
const PER_PAGE = 25
let _bookFilter = ''       // bookRaw del libro activo en sidebar ('' = todos)
let clipFontSize           // tamaño fuente detalle libro (localStorage)
let hlFontSize             // tamaño fuente highlights búsqueda (localStorage)
let currentBookDetail      // libro abierto en screen-book-detail
let bookDetailFilter = ''  // filtro textual dentro del detalle
let allClippings = []
const hiddenBooks          // Set de bookRaw ocultos (localStorage)
const coverCache = {}      // { 'título|autor': 'url' } — persiste en IDB
const LIBRARY = {}         // { cat: [{ raw, t, a, k, c[] }] } — poblado por renderLibrary()
```

---

## Funciones clave

### Flujo de datos al cargar un archivo

```
loadFile(txt)
  → parseKindleClippings(text)         // parsea My_Clippings.txt
  → filterClippingsAll(rawClips)       // para allClippings: dedup, sin cap chars
  → filterClippings(rawClips)          // para BM25: dedup, max 1200 chars, SIN cap por libro
  → buildBM25(clippings.map(c=>c.text))
  → persistIndex()                     // guarda en IndexedDB
  → renderLibrary() + populateSidebarBooks()
```

### Carga automática (IndexedDB)

```javascript
async function tryAutoLoad()
  // Abre IDB → restaura clippings + allClippings + coverCache
  // → buildBM25 → show('screen-app') → renderLibrary() → populateSidebarBooks()
```

### Persistencia IDB

```javascript
async function persistIndex()
  // Guarda { version, saved, clippings, allClippings, coverCache } en IDB
  // Se llama después de: loadFile, mergeSource, loadIndex

window.clearAndReset()
  // Borra IDB, resetea estado, vuelve a screen-upload
```

### Búsqueda

```javascript
window.doSearch()
  // Resetea _bookFilter y sidebar a "Todos"
  // Llama switchTab('search')
  // currentResults = bm25Search(q)
  // renderResults(terms)

window.renderResults(terms)
  // Filtra currentResults por _bookFilter (si hay)
  // Renderiza .h-card con .h-text + .h-share-btn
  // Llama renderPagination()
```

### Navegación sidebar

```javascript
window.switchTab(tab)  // 'search' | 'library'
  // Muestra/oculta search-content y screen-library
  // Si library: programa scheduleCoverFetch()

window.filterByBook(bookRaw)
  // SIEMPRE modo browse (no hereda búsqueda activa)
  // Resetea currentResults = [], _bookFilter = '', search-input.value = ''
  // Si bookRaw: muestra todos los clips de allClippings para ese libro
  // Si '': vuelve al estado inicial vacío
  // NO toca currentResults (doSearch siempre es búsqueda global fresca)
```

### Biblioteca

```javascript
window.renderLibrary()
  // buildLibraryFromClippings() → llena LIBRARY
  // Renderiza grilla de libros por categoría
  // scheduleCoverFetch() para cargar tapas

buildLibraryFromClippings()
  // Fuente: allClippings (sin cap)
  // Categoriza cada libro via categorizeBook(title, author) con CAT_KEYWORDS
  // Retorna { cat: [{ raw, t, a, k, c[] }] }

window.showBook(ci, bi)
  // LIBRARY[CAT_ORDER[ci]][bi] → currentBookDetail
  // renderBookDetailClips('') → show('screen-book-detail')

window.backToLibrary()
  // show('screen-app') + switchTab('library')
```

### Compartir en X

```javascript
window.shareResult(idx)   // desde resultados de búsqueda o browse
window.shareClip(idx)     // desde screen-book-detail

// Ambos llaman generateQuoteCard(d) → canvas 1200×628px
// → blob → navigator.clipboard.write() → window.open(x.com/intent/tweet)
// _resultShareData[idx] = { text, title, author, bookRaw }
```

### Sidebar books — generación de botones

```javascript
function populateSidebarBooks()
  // Cuenta desde allClippings (no clippings) para mostrar total real
  // onclick="filterByBook(this.dataset.book)"  ← usa dataset, NO JSON.stringify
  // data-book="${esc(b)}"                       ← HTML-safe
```

---

## Pantallas (`show(id)`)

| ID | Display | Descripción |
|----|---------|-------------|
| `screen-upload` | block | Pantalla inicial, drag & drop |
| `screen-progress` | flex | Barra de progreso al procesar |
| `screen-app` | **flex** | App principal (sidebar + main) |
| `screen-book-detail` | block | Detalle de libro (fuera de #screen-app) |

---

## IndexedDB schema

```javascript
DB: 'kindleBrain', store: 'index', key: 'current'
{
  version: 1,
  saved: Date.toISOString(),
  clippings: [...],      // array para BM25 (max 1200 chars, dedup)
  allClippings: [...],   // array completo sin cap
  coverCache: {}         // { 'title|author': 'url' }
}
```

---

## Formatos de clip (objeto)

```javascript
{
  bookRaw: "Título del libro (Apellido, Nombre)",  // key canónico
  bookTitle: "Título del libro",
  bookAuthor: "Nombre Apellido",
  text: "Texto del subrayado...",
  year: 2023,
  hybrid: 0.0–1.0   // score normalizado de BM25 (0 si es browse)
}
```

---

## Bugs resueltos (historial)

### 1. onclick roto en sidebar books
**Causa:** `JSON.stringify(b)` produce `"título"` con comillas dobles dentro de `onclick="..."` → HTML roto.  
**Fix:** `onclick="filterByBook(this.dataset.book)"` + `data-book="${esc(b)}"`.

### 2. Click en libro no mostraba nada (sin búsqueda previa)
**Causa:** `filterByBook` llamaba `renderResults()` que filtra `currentResults` → vacío si no hubo búsqueda.  
**Fix:** `filterByBook` ahora siempre muestra clips desde `allClippings` directamente.

### 3. Buscador roto después de click en libro
**Causa:** `_bookFilter` quedaba activo tras click → `doSearch` heredaba el filtro → resultados filtrados a un solo libro.  
**Fix:** `doSearch` resetea `_bookFilter = ''` y sidebar a "Todos" antes de buscar. `filterByBook` también resetea `currentResults`.

### 4. Cap de 80 subrayados por libro
**Causa:** `filterClippings` tenía `bookCounts[c.bookRaw] <= 80` para rendimiento BM25.  
**Fix:** Cap eliminado. Solo queda max 1200 chars por clip (textos muy largos aportan poco al BM25).

### 5. Contador del sidebar mostraba máx 80
**Causa:** `populateSidebarBooks` contaba desde `clippings` (capped) en lugar de `allClippings`.  
**Fix:** `allClippings.forEach(c => { counts[c.bookRaw]++ })`.

### 6. Tapas de libros incorrectas / duplicadas
**Causa:** Open Library devolvía libros por título sin validar coincidencia.  
**Fix:** Validación de 60% word-overlap entre título buscado y resultado antes de aceptar la cover.

### 7. `show('screen-app')` rompía el sidebar layout
**Causa:** `show()` usaba `display:block` para `screen-app` pero el layout necesita `display:flex`.  
**Fix:** `if (s === 'screen-app') el.style.display = 'flex'`.

### 8. Biblioteca vacía al cargar desde JSON (Boox)
**Causa:** `filterClippingsAll` tenía limite de 900 chars que excluía clips válidos; `renderLibrary` no se llamaba al mergear.  
**Fix:** Límite removido de `filterClippingsAll`; `renderLibrary()` llamado en todos los flujos de carga.

---

## Fuentes de datos soportadas

1. **My_Clippings.txt** (Kindle) — formato `==========` como separador
2. **JSON de otro lector** (Boox y similares) — parseado via `parseNewReaderJSON()`
3. **Merge de múltiples fuentes** — se combinan y deduplan en `mergeSource()`

---

## Features implementados (en orden cronológico)

1. Búsqueda BM25 sobre My_Clippings.txt
2. Soporte Boox (JSON de otro lector)
3. Merge de múltiples fuentes
4. Biblioteca dinámica categorizada por keywords
5. Tapas de libros via Open Library API
6. Buscador dentro de Biblioteca (`#lib-search`)
7. Página de detalle por libro (`screen-book-detail`) con slider de fuente
8. Botón ocultar libro
9. Rediseño UI: paleta blanco/negro tipo Readwise
10. Sidebar layout (250px fijo, sticky)
11. Búsqueda accent-insensitive (`normTxt()` via NFD)
12. Compartir en X con quote card generada en Canvas (1200×628, cover incluida)
13. Persistencia automática en IndexedDB (carga instantánea al reabrir)
14. Slider de fuente en highlights de búsqueda (`#hl-font-slider`)
15. Centralizado de resultados (`#results { margin: 0 auto }`)
16. Browse por libro desde sidebar (muestra todos los clips sin cap)

---

## Pendientes / ideas futuras

- Buscar DENTRO de un libro (combinar `filterByBook` + `doSearch` con scope)
- Tags manuales por subrayado
- Export de highlights seleccionados
- Orden alternativo en resultados (cronológico, por libro)
- Resumen automático por libro
