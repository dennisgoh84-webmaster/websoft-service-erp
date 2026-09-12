import { useState } from 'react'

// Shared advertisement video -- shown tall and wide beside the Login
// form, and smaller beside every page after signing in (2026-09-12:
// "after login successfully, all modules, hide menu bar, then have
// smaller tall banner on the right for advertisement video"; the Login
// version itself was changed from a static text panel to video in the
// same conversation, "the right advert panel sample picture can change
// to video instead"). No real advertisement video exists yet, so this
// is a clearly-labelled placeholder -- MDN's own CC0 sample clip,
// hosted on Mozilla's infrastructure, so it won't disappear or show
// anything inappropriate. Swap PROMO_VIDEO_URL for the real ad once one
// exists; same "ask if this should be editable from Company Setup"
// question as the caption text applies here too.
export const PROMO_VIDEO_URL = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
export const PROMO_CAPTION =
  "What's New: Reference Monitor, icon Print/Email/WhatsApp actions, and Company/Individual."

/** `className` picks the size/placement (see .login-promo vs
 * .app-ad-banner in index.css) -- the video/caption/fallback behaviour
 * is identical either way. */
export default function PromoVideoPanel({ className }: { className: string }) {
  // If the video can't load (blocked network, bad URL, browser codec
  // support), fall back to the plain gradient panel + caption instead
  // of showing a broken black box.
  const [videoFailed, setVideoFailed] = useState(false)

  return (
    <aside className={className}>
      {!videoFailed && (
        <video
          className="promo-video"
          src={PROMO_VIDEO_URL}
          autoPlay
          muted
          loop
          playsInline
          onError={() => setVideoFailed(true)}
        />
      )}
      <p className="promo-caption">{PROMO_CAPTION}</p>
    </aside>
  )
}
