// Records a video walkthrough of the confirmed Service Operations
// workflow (SRV-001..018) for Websoft Service ERP Solution:
// Customer -> Contract -> Ticket -> Timesheet -> Contract Hour
// Validation -> Excess Review (Nico) -> Invoice.
//
// Run with: node record_demo.js
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const OUT_DIR = '/tmp/websoft_demo_video'
const BASE_URL = 'http://127.0.0.1:5173'
const PAUSE = 1400 // ms between narrated steps, so the video is watchable

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

  // 1. Login as Nico (Service & Support lead -- SRV-004's confirmed reviewer)
  await page.goto(`${BASE_URL}/login`)
  await pause(800)
  await page.fill('input[type=email]', 'nico@websoft.local')
  await page.fill('input[type=password]', 'demo1234')
  await pause(500)
  await page.click('button[type=submit]')
  await page.waitForURL('**/')
  await pause()

  // 2. Customers
  await page.waitForTimeout(300)
  await pause()

  // 3. Contracts -> open Acme's contract, show hours + confirmed rule labels
  await page.click('text=Contracts')
  await page.waitForTimeout(400)
  await pause()
  await page.click('text=Open')
  await page.waitForTimeout(400)
  await pause(2000) // let the viewer read the SRV-001/002/004/008 labels & progress bar

  // 4. Tickets -> open the VPN ticket
  await page.click('text=Tickets')
  await page.waitForTimeout(400)
  await pause()
  await page.click('text=Open')
  await page.waitForTimeout(400)
  await pause(1800) // read the timesheet table: 540/600 min consumed so far

  // 5. Approve the pending timesheet entry -- this is the moment SRV-003/
  //    SRV-004/SRV-007 fire: 80 raw min rounds to 90, only 60 remain, so
  //    the contract exhausts AND an Excess Usage record is created.
  await page.click('button:has-text("Approve")')
  await page.waitForTimeout(600)
  await pause(2000)

  // 6. Back to the contract -- now Exceeded, with the excess usage visible
  await page.click('text=Contracts')
  await pause(600)
  await page.click('text=Open')
  await page.waitForTimeout(400)
  await pause(2200)

  // 7. Excess Review -- Nico decides: billable, with a reason (SRV-004/008/013)
  await page.click('text=Excess Review')
  await page.waitForTimeout(500)
  await pause(1500)
  await page.selectOption('select', 'billable')
  await pause(600)
  await page.fill('textarea', 'Customer requested urgent after-hours VPN fix beyond contracted hours; approved as billable at standard contract rate.')
  await pause(800)
  await page.click('button:has-text("Record decision")')
  await page.waitForTimeout(600)
  await pause(2000) // show it move to "Decided"

  // 8. Invoices -- the new excess-usage invoice at the blended rate (SRV-008)
  await page.click('text=Invoices')
  await page.waitForTimeout(500)
  await pause(3000)

  await context.close()
  await browser.close()

  const files = fs.readdirSync(OUT_DIR).filter((f) => f.endsWith('.webm'))
  console.log('Video saved:', files.map((f) => path.join(OUT_DIR, f)))
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
