// Small circular staff avatar -- shows the uploaded photo (Staff
// Master) if there is one, else the person's initials on a neutral
// background. Confirmed 2026-09-11: used on Support Monitoring and
// Staff Master so a photo (once set) shows up everywhere staff are
// listed, not just one screen.
function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export default function StaffAvatar({
  photo,
  fullName,
  size = 28,
}: {
  photo: string | null | undefined
  fullName: string
  size?: number
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        borderRadius: '50%',
        overflow: 'hidden',
        background: 'var(--accent)',
        color: 'var(--accent-contrast)',
        fontSize: Math.max(10, size * 0.4),
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {photo ? (
        <img src={photo} alt={fullName} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : (
        initials(fullName)
      )}
    </span>
  )
}
