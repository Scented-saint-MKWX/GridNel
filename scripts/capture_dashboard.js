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

    // Wait for map and camera nodes
    await page.waitForSelector("#map");
    await new Promise(r => setTimeout(r, 2000));

    console.log("Triggering trajectory tracking for vehicle MH12AB1284...");
    await page.evaluate(() => {
        trackPlate("MH12AB1284");
    });

    // Wait for OSRM road route and Leaflet markers to render
    await new Promise(r => setTimeout(r, 6000));

    const outputPath = path.join(__dirname, "..", "trajectory_dashboard.png");
    await page.screenshot({ path: outputPath, fullPage: false });
    console.log(`Screenshot saved successfully to: ${outputPath}`);

    await browser.close();
}

capture().catch(err => {
    console.error("Screenshot capture error:", err);
    process.exit(1);
});
