const puppeteer = require('puppeteer');
const path = require('path');

async function capture() {
    console.log("Launching headless browser...");
    const browser = await puppeteer.launch({
        headless: "new",
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    console.log("Navigating to SentinelGrid dashboard at http://localhost:8000/ ...");
    await page.goto("http://localhost:8000/", { waitUntil: "networkidle0", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2500));

    // 1. Capture Analytics Mode with Heatmap
    console.log("Switching to Analytics Mode with Traffic Density Heatmap...");
    await page.evaluate(() => {
        setMode('analytics');
        inspectCamera('CAM_241');
    });
    await new Promise(r => setTimeout(r, 4000));

    const analyticsPath = path.join("/work", "analytics_dashboard.png");
    await page.screenshot({ path: analyticsPath, fullPage: false });
    console.log(`Analytics screenshot saved successfully to: ${analyticsPath}`);

    // 2. Capture Tracking Mode with Road Route
    console.log("Switching to Tracking Mode with Road Route for MH12AB1284...");
    await page.evaluate(() => {
        setMode('tracking');
        trackPlate("MH12AB1284");
    });
    await new Promise(r => setTimeout(r, 4000));

    const trackingPath = path.join("/work", "trajectory_dashboard.png");
    await page.screenshot({ path: trackingPath, fullPage: false });
    console.log(`Tracking screenshot saved successfully to: ${trackingPath}`);

    await browser.close();
}

capture().catch(err => {
    console.error("Screenshot capture error:", err);
    process.exit(1);
});
