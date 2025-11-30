# Aelion Systems - UI/UX Design System Document

This document serves as the single source of truth for the UI/UX design of the Aelion Systems frontend. It details all design decisions, style guides, and component specifications derived from the current implementation.

## 1. Brand Identity & Color Palette

### Primary Colors
*   **Brand Primary (Slate 900):** `#0f172a`
    *   *Usage:* Main background for Hero sections, Footer, Dark cards, Primary Text.
*   **Brand Accent (Blue 500/600):** `#3b82f6` (Tailwind blue-500) / `#2563eb` (Tailwind blue-600)
    *   *Usage:* Primary Buttons, Active Navigation Links, Icons, Highlights.
*   **Brand Cyan (Cyan 300):** `#67e8f9`
    *   *Usage:* Gradients, secondary accents in dark modes.

### Neutral Colors
*   **Background (White):** `#ffffff`
    *   *Usage:* Main content areas, cards.
*   **Background Alt (Slate 50):** `#f8fafc`
    *   *Usage:* Page backgrounds, section differentiation.
*   **Text Primary (Slate 900):** `#0f172a`
    *   *Usage:* Headings, main body text.
*   **Text Secondary (Slate 600/700):** `#475569` / `#334155`
    *   *Usage:* Paragraphs, descriptions, inactive links.
*   **Text Muted (Slate 300/400):** `#cbd5e1` / `#94a3b8`
    *   *Usage:* Footer text, descriptions on dark backgrounds.
*   **Borders (Slate 100/200):** `#f1f5f9` / `#e2e8f0`
    *   *Usage:* Card borders, separators, header border.

### Gradients
*   **Text Gradient:** `bg-gradient-to-r from-blue-400 to-cyan-300`
    *   *Usage:* Hero headlines for emphasis (e.g., "Defend").
*   **Dark Overlay:** `bg-gradient-to-b from-slate-900/80 via-slate-900/50 to-slate-900`
    *   *Usage:* Hero video overlays.
*   **Card Gradient:** `bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent`
    *   *Usage:* Text readability overlay on image-heavy cards.

---

## 2. Typography

### Font Families
*   **Display Font (Headings):** `Michroma`, sans-serif
    *   *Source:* Google Fonts (inferred).
    *   *Characteristics:* Technical, futuristic, wide stance.
*   **Body Font (Content):** `Inter`, system-ui, -apple-system, sans-serif
    *   *Source:* Google Fonts (inferred).
    *   *Characteristics:* Clean, legible, modern sans-serif.
*   **Monospace:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`
    *   *Usage:* Typing effects, code snippets.

### Hierarchy & Scaling
*   **H1 (Hero):** `text-5xl md:text-7xl` | `font-bold` | `font-display` | `tracking-wide`
*   **H2 (Section):** `text-3xl md:text-4xl` | `font-bold` | `font-display` | `tracking-wide`
*   **H3 (Card):** `text-xl md:text-2xl` | `font-bold` | `font-display`
*   **Subtitle/Label:** `text-sm` | `uppercase` | `tracking-wider` | `font-semibold` | `text-blue-400`
*   **Body:** `text-base` or `text-lg` (intro) | `text-slate-600` | `leading-relaxed`
*   **Nav Links:** `text-sm` | `uppercase` | `tracking-widest` | `font-bold` | `font-display`
*   **Footer Headings:** `text-sm` | `uppercase` | `tracking-wider` | `font-bold` | `font-display`

---

## 3. Layout & Structure

### Global Layout
*   **Header:** Fixed positioning (`fixed top-0`), Height `h-24` (96px).
*   **Main Content:** Top padding `pt-24` to prevent overlap with fixed header.
*   **Footer:** Vertical padding `py-16`.
*   **Container:** `container mx-auto px-6` used consistently to center content with horizontal padding.

### Grid Systems
*   **Standard Grid:** `grid md:grid-cols-2` or `md:grid-cols-3` or `md:grid-cols-4`.
*   **Gap:** Standard gap is `gap-8` (2rem) or `gap-12` (3rem).
*   **Responsive Breakpoint:** `md` (768px) is the primary breakpoint for switching from stacked to grid layouts.

### Spacing
*   **Section Padding:** `py-24` (6rem) for standard content sections.
*   **Internal Card Padding:** `p-8` or `p-10`.

---

## 4. Components & UI Elements

### Navigation Bar
*   **Background:** White with 90% opacity (`bg-white/90`) and backdrop blur (`backdrop-blur-md`).
*   **Border:** Bottom border `border-slate-200`.
*   **Transitions:** `transition-all duration-300`.
*   **Logo:** `h-12` (mobile) to `h-16` (desktop).
*   **Mobile Menu:** Full-width dropdown, animating height and opacity.

### Buttons
*   **Primary Action:**
    *   Background: `bg-blue-600`
    *   Hover: `hover:bg-blue-700`
    *   Text: White, `font-semibold`
    *   Shape: `rounded-lg` or `rounded-xl`
    *   Padding: `px-8 py-4` (Large) or `px-10 py-5`
    *   Effect: `hover:scale-105` transition
*   **Secondary Action:**
    *   Border: `border border-slate-600`
    *   Hover: `hover:bg-slate-800`
    *   Text: White (on dark bg)
    *   Shape: `rounded-lg`
*   **Text Link:**
    *   Color: `text-blue-600`
    *   Hover: `hover:text-blue-700`
    *   Icon: Paired with `ChevronRight` or `ArrowRight`.

### Cards (Value Prop / Features)
*   **Background:** `bg-white`
*   **Border:** `border border-slate-100`
*   **Shadow:** `shadow-lg`
*   **Radius:** `rounded-2xl`
*   **Hover Effect:** `whileHover={{ y: -5 }}` (lift up), Border color change to `blue-100`.
*   **Icon Container:** `w-16 h-16 rounded-xl bg-blue-50 flex items-center justify-center`.

### Project Cards (Dark)
*   **Background:** `bg-slate-900`
*   **Overlay:** Gradient `from-slate-900` to transparent.
*   **Texture:** Noise SVG overlay (`opacity-20`).
*   **Content:** Text overlay at the bottom. Description fades in on hover (`opacity-0` -> `opacity-100`).
*   **Tag:** Small pill `bg-blue-600 text-white text-xs font-bold rounded-full`.

### Effects & Textures
*   **Noise Texture:** Used on dark backgrounds (`/assets/noise.svg` or external URL) with `mix-blend-overlay` and low opacity (20%).
*   **Glassmorphism:** Used in Header (`backdrop-blur-md`).
*   **Shadows:** `shadow-lg` used on cards for depth. `shadow-2xl` for prominent dark cards.

### Icons
*   **Library:** Lucide React (`lucide-react`)
*   **Style:** Line icons.
*   **Size:** Standard `size={20}` for buttons, `w-8 h-8` for feature icons.
*   **Color:** Matches text or brand accent (`text-blue-600`).

---

## 5. Animation (Framer Motion)

*   **Page Transitions:**
    *   `initial={{ opacity: 0 }}`
    *   `animate={{ opacity: 1 }}`
    *   `exit={{ opacity: 0 }}`
    *   `duration: 0.5s`
*   **Entrance Animations:**
    *   Slide Up: `initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}`
    *   Slide In (Left/Right): `initial={{ x: -20, opacity: 0 }} whileInView={{ x: 0, opacity: 1 }}`
    *   Staggered delays: `0.2s`, `0.4s`, `0.6s`.
*   **Micro-interactions:**
    *   Hover Scale: `whileHover={{ scale: 1.05 }}` or `scale: 1.02`.
    *   Hover Lift: `whileHover={{ y: -5 }}`.

---

## 6. Responsive Strategy

*   **Mobile First:** Tailwind utility classes are mobile-first (default applies to all, `md:` applies to desktop).
*   **Navigation:**
    *   Mobile: Hamburger menu (`<Menu />`) toggles a full-width vertical list.
    *   Desktop: Horizontal list in header.
*   **Typography:**
    *   Headings scale using responsive prefixes (e.g., `text-5xl md:text-7xl`).
*   **Layouts:**
    *   Flex columns on mobile (`flex-col`), Rows on desktop (`md:flex-row`).
    *   Grids start at 1 column, expand to 2/3/4 on `md`.

## 7. Accessibility Considerations (Inferred)
*   **Contrast:** High contrast maintained (Slate 900 on White, White on Slate 900).
*   **Focus States:** Standard browser focus rings (Tailwind defaults).
*   **Semantic HTML:** Use of `<header>`, `<main>`, `<footer>`, `<nav>`, `<button>`, `<h1>`-`<h6>`.
*   **Alt Text:** Required on all `<img>` tags (e.g., "Aelion Systems", "Logo").
