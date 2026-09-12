// Records a video walkthrough of the security/PDPA/admin work added
// 2026-09-12: company logo + advertisement video on the Login page,
// "Forgot password" via email OTP, forced password-change on a new
// staff member's first sign-in, the app-wide hidden menu bar + smaller
// ad banner on every page, the PDPA & Data Retention section on
// Company/Individual (consent checkbox + timestamp, signed-agreement
// upload/preview, data-expiry-gated Archive button), and the new
// Announcements & Ad Banner admin screen (edit the video/updates and
// see them appear on the banner).
//
// Run with: node record_security_pdpa_demo.cjs
// Requires: backend + frontend dev servers running, a freshly seeded
// DB, AND two pieces of test data seeded first (see
// docs/video-walkthrough-setup.md / the session notes):
//   1. A staff account with must_change_password=True (this script
//      expects "aisha@websoft.local" / "Temp1234").
//   2. A password_reset LoginOtp row for dennis@websoft.local with a
//      known code (this script expects "135790") -- stands in for the
//      email that would really be sent once SMTP is configured; every
//      other step of the reset runs through the real code path.
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const OUT_DIR = '/tmp/websoft_security_pdpa_video'
const BASE_URL = 'http://127.0.0.1:5173'
const PAUSE = 1200
const SAMPLE_IMAGE = '/tmp/claude-0/-home-user-webmaster-erp/scratchpad/signed-agreement-sample.png'

function rmrf(p) {
  if (fs.existsSync(p)) fs.rmSync(p, { recursive: true, force: true })
}

async function pause(ms = PAUSE) {
  await new Promise((r) => setTimeout(r, ms))
}

async function main() {
  rmrf(OUT_DIR)
  fs.mkdirSync(OUT_DIR, { recursive: true })

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 800 } },
  })
  const page = await context.newPage()

  // 1. Login page: company logo + advertisement video panel.
  await page.goto(`${BASE_URL}/login`)
  await pause(2500)

  // 2. Forgot password -- email + OTP, no separate reset link/token.
  await page.getByRole('button', { name: 'Forgot password?' }).click()
  await pause(900)
  await page.locator('input[type="email"]').fill('dennis@websoft.local')
  await pause(500)
  await page.getByRole('button', { name: 'Send reset code' }).click()
  await pause(1500) // generic message shown either way -- never confirms the email exists

  await page.locator('input[inputmode="numeric"]').fill('135790')
  await pause(400)
  const resetPwInputs = await page.locator('input[type="password"]').all()
  await resetPwInputs[0].fill('Demo12345')
  await resetPwInputs[1].fill('Demo12345')
  await pause(600)
  await page.getByRole('button', { name: 'Reset password' }).click()
  await pause(1800) // back on the credentials step with a success message

  // 3. Sign in as a brand-new staff account -- forced first-login
  //    password change (never their own choice of a temporary password).
  await page.locator('input[type="email"]').fill('aisha@websoft.local')
  await page.locator('input[type="password"]').fill('Temp1234')
  await pause(500)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await pause(1500)

  const newPwInputs = await page.locator('input[type="password"]').all()
  await newPwInputs[0].fill('Aisha2026Secure')
  await newPwInputs[1].fill('Aisha2026Secure')
  await pause(600)
  await page.getByRole('button', { name: 'Set password and sign in' }).click()
  await page.waitForURL('**/', { timeout: 10000 })
  await pause(1200)

  // 4. Now signed in -- the menu bar is hidden by default on every
  //    page, with a smaller version of the same ad banner running the
  //    full height on the right. Peek the menu open, then let it
  //    re-hide on the next navigation.
  await pause(1500)
  await page.getByRole('button', { name: '☰ Menu' }).click()
  await pause(1800)

  // 5. Sign out of the limited new-hire account, back in as Dennis
  //    (Owner) for the admin screens below.
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.waitForURL('**/login', { timeout: 10000 })
  await pause(600)
  await page.locator('input[type="email"]').fill('dennis@websoft.local')
  await page.locator('input[type="password"]').fill('Demo12345') // the password just reset above
  await pause(400)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL('**/', { timeout: 10000 })
  await pause(1000)

  // 6. Company / Individual -> Acme Manufacturing -> PDPA & Data
  //    Retention: tick consent (server-stamped date/time), upload the
  //    signed agreement, set a past data-expiry date, and archive.
  await page.getByRole('button', { name: '☰ Menu' }).click()
  await pause(500)
  await page.getByRole('link', { name: 'Company / Individual', exact: true }).click()
  await pause(900)
  await page.getByRole('link', { name: 'Acme Manufacturing Pte Ltd' }).click()
  await pause(1000)

  const pdpaHeading = page.getByRole('heading', { name: 'PDPA & Data Retention' })
  await pdpaHeading.scrollIntoViewIfNeeded()
  await pause(500)
  await page.click('text=PDPA Agreement e-signed')
  await pause(1500) // the recorded date/time appears immediately below

  await page.locator('input[type="file"]').setInputFiles(SAMPLE_IMAGE)
  await pause(1800) // preview + Remove button appear

  await pdpaHeading.scrollIntoViewIfNeeded()
  await page.locator('input[type="date"]').fill('2020-01-01')
  await pause(400)
  await page.getByRole('button', { name: 'Save changes' }).click()
  await pause(1200)

  await pdpaHeading.scrollIntoViewIfNeeded()
  await pause(1200) // the "Past expiry -- archive this record" badge + Archive now button
  await page.getByRole('button', { name: 'Archive now' }).click()
  await pause(1800) // Archived timestamp + Unarchive

  // 7. Maintenance -> Announcements & Ad Banner: change the video URL
  //    and add a new "What's New" item, then see it live on the banner.
  await page.getByRole('button', { name: '☰ Menu' }).click()
  await pause(500)
  await page.getByRole('link', { name: 'Announcements & Ad Banner', exact: true }).click()
  await pause(1200)

  await page.getByPlaceholder('e.g. New, Update, Add-on').fill('New')
  await page.getByPlaceholder('e.g. Forgot password + email OTP is now live.').fill(
    'You can now edit this banner yourself from Maintenance.',
  )
  await pause(500)
  await page.getByRole('button', { name: 'Add announcement' }).click()
  await pause(1500)

  await page.reload({ waitUntil: 'networkidle' }) // "next load" picks up the change
  await pause(2500) // the new item now shows on the ad banner, right there in the same viewport

  await context.close()
  await browser.close()

  const files = fs.readdirSync(OUT_DIR).filter((f) => f.endsWith('.webm'))
  console.log('Video saved:', files.map((f) => path.join(OUT_DIR, f)))
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
