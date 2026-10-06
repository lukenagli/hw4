// Original decorative artwork for the "varsity print shop" look.
// Plain SVG shapes only: no official Yale marks, logos or mascot art.

/** Round chenille-style shop patch with stitched edge and the CC monogram. */
export function ShopPatch({ size = 52 }: { size?: number }) {
  return (
    <svg className="shop-patch" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="31" fill="var(--cream)" />
      <circle cx="32" cy="32" r="27" fill="var(--blue)" />
      <circle cx="32" cy="32" r="23.5" fill="none" stroke="var(--cream)" strokeWidth="1.4" strokeDasharray="3 2.4" />
      <text
        x="32"
        y="39.5"
        textAnchor="middle"
        fontFamily="Graduate, Georgia, serif"
        fontSize="21"
        fill="var(--cream)"
        letterSpacing="-0.5"
      >
        CC
      </text>
    </svg>
  )
}

/** "Stitch", the counter assistant: a needle threading a looped S through a round patch. */
export function StitchAvatar({ size = 36 }: { size?: number }) {
  return (
    <svg className="stitch-avatar" width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="19" fill="var(--cream)" stroke="var(--blue)" strokeWidth="2" />
      <circle cx="20" cy="20" r="15" fill="none" stroke="var(--blue)" strokeWidth="1" strokeDasharray="2 2" opacity="0.55" />
      {/* thread: a loose S */}
      <path
        d="M25 11.5c-3-2-8-1.2-8.6 2.2-.7 3.9 7.8 3.5 7.6 8.1-.2 4-6 5.2-9.6 2.6"
        fill="none"
        stroke="var(--blue)"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      {/* needle */}
      <path d="M27.5 8.5 13 29" stroke="var(--ink)" strokeWidth="1.8" strokeLinecap="round" />
      <ellipse cx="27" cy="9.3" rx="1.1" ry="2" transform="rotate(35 27 9.3)" fill="var(--cream)" stroke="var(--ink)" strokeWidth="1" />
    </svg>
  )
}

/** Small felt pennant used beside section titles. */
export function Pennant({ label }: { label: string }) {
  return (
    <span className="pennant" aria-hidden="true">
      <span>{label}</span>
    </span>
  )
}

/** Ask the chat panel (which lives in the layout) to open, optionally sending a question. */
export function openChat(question?: string) {
  window.dispatchEvent(new CustomEvent('cc:open-chat', { detail: { question } }))
}
