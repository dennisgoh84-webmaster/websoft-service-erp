import { useState } from 'react'
import { NavLink } from 'react-router-dom'

export interface NavItem {
  /** Stable identity for ordering -- the route path works well since it
   * never changes for a given screen. */
  key: string
  path: string
  label: string
  /** Whether Group Authority + Module Control let this user see it right
   * now (see the `can()` helper in Layout.tsx). Hidden items still hold
   * their place in the saved order, so they reappear where the user left
   * them if access is granted later. */
  visible: boolean
}

function loadOrder(storageKey: string): string[] {
  try {
    const raw = localStorage.getItem(storageKey)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/** One collapsible, reorderable sidebar section (Operations / Accounts /
 * Maintenance). Confirmed 2026-09-11: "let me choose the sequence for the
 * menu bar" -- drag a link up/down within its own section to reorder it;
 * the order is a per-browser display preference (localStorage), same as
 * the collapse state, not a Group Authority setting -- it never changes
 * what a user can see, only where it appears in the list. Dragging across
 * sections is not supported -- a link stays in the section its module
 * belongs to. */
export default function NavSection({
  sectionKey,
  title,
  items,
  collapsed,
  onToggle,
}: {
  sectionKey: string
  title: string
  items: NavItem[]
  collapsed: boolean
  onToggle: () => void
}) {
  const storageKey = `websoft_nav_order_${sectionKey}`
  const [order, setOrder] = useState<string[]>(() => loadOrder(storageKey))
  const [dragKey, setDragKey] = useState<string | null>(null)

  const allKeys = items.map((i) => i.key)
  const orderedKeys = [...order.filter((k) => allKeys.includes(k)), ...allKeys.filter((k) => !order.includes(k))]
  const byKey = new Map(items.map((i) => [i.key, i]))
  const visibleOrdered = orderedKeys.map((k) => byKey.get(k)!).filter((i) => i.visible)

  if (visibleOrdered.length === 0) return null

  function persist(next: string[]) {
    setOrder(next)
    try {
      localStorage.setItem(storageKey, JSON.stringify(next))
    } catch {
      /* private browsing / storage blocked -- order just won't persist */
    }
  }

  function onDrop(targetKey: string) {
    if (!dragKey || dragKey === targetKey) {
      setDragKey(null)
      return
    }
    const next = orderedKeys.slice()
    const from = next.indexOf(dragKey)
    const to = next.indexOf(targetKey)
    if (from === -1 || to === -1) {
      setDragKey(null)
      return
    }
    next.splice(from, 1)
    next.splice(to, 0, dragKey)
    persist(next)
    setDragKey(null)
  }

  return (
    <div className="nav-section">
      <button
        type="button"
        className="nav-section-label"
        aria-expanded={!collapsed}
        onClick={onToggle}
      >
        <span>{title}</span>
        <span className="nav-section-chevron">{collapsed ? '▸' : '▾'}</span>
      </button>
      {!collapsed && (
        <>
          {visibleOrdered.map((item) => (
            <div
              key={item.key}
              className={`nav-item-row${dragKey === item.key ? ' dragging' : ''}`}
              draggable
              onDragStart={() => setDragKey(item.key)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(item.key)}
              onDragEnd={() => setDragKey(null)}
              title="Drag to reorder"
            >
              <span className="nav-drag-handle" aria-hidden="true">
                ⠿
              </span>
              <NavLink to={item.path}>{item.label}</NavLink>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
