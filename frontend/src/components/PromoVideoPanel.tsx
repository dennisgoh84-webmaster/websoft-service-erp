import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { PublicAdBanner } from '../lib/api'

// Shared advertisement video + "What's New" items -- shown tall and
// wide beside the Login form, and smaller beside every page after
// signing in (2026-09-12: "after login successfully, all modules, hide
// menu bar, then have smaller tall banner on the right for
// advertisement video"). Content is admin-editable from the
// Announcements screen under Maintenance (2026-09-12: "is there a
// place for me to set all these advertisements or latest updates and
// push publish") -- Save there is live immediately, so this always
// reads the current published content via the one unauthenticated
// endpoint (non-sensitive, identical for every viewer, and the Login
// page needs it before anyone has signed in anyway).
export default function PromoVideoPanel({ className }: { className: string }) {
  const [banner, setBanner] = useState<PublicAdBanner | null>(null)
  // If the video can't load (blocked network, bad URL, browser codec
  // support), fall back to the plain gradient panel + items instead of
  // showing a broken black box.
  const [videoFailed, setVideoFailed] = useState(false)

  useEffect(() => {
    api
      .getPublicAdBanner()
      .then(setBanner)
      .catch(() => setBanner(null))
  }, [])

  const videoUrl = banner?.video_url ?? null

  return (
    <aside className={className}>
      {videoUrl && !videoFailed && (
        <video
          className="promo-video"
          src={videoUrl}
          autoPlay
          muted
          loop
          playsInline
          onError={() => setVideoFailed(true)}
        />
      )}
      {banner && banner.items.length > 0 && (
        <div className="promo-items">
          {banner.items.map((item) => (
            <div className="promo-item" key={item.id}>
              {item.tag && <span className="promo-item-tag">{item.tag}</span>}
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}
