const puppeteer = require('puppeteer');
const path = require('path');

async function test() {
    console.log("Launching headless browser for verification...");
    const browser = await puppeteer.launch({
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    console.log("1. Navigating to http://localhost:8000/ ...");
    await page.goto("http://localhost:8000/", { waitUntil: "networkidle0", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));

    // Test 1: Generate trajectory in Tracking mode
    console.log("2. Tracking MH12AB1284...");
    await page.evaluate(() => {
        setMode('tracking');
        trackPlate('MH12AB1284');
    });
    await new Promise(r => setTimeout(r, 4000));

    let polylinesCount1 = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return count;
    });
    console.log(`Polylines in Tracking Mode: ${polylinesCount1} (Expected >= 1)`);
    if (polylinesCount1 < 1) throw new Error("Trajectory polyline was not plotted in tracking mode!");

    // Test 2: Switch back to Analytics mode
    console.log("3. Switching back to Analytics mode...");
    await page.evaluate(() => {
        setMode('analytics');
    });
    await new Promise(r => setTimeout(r, 3000));

    let polylinesCount2 = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return count;
    });
    console.log(`Polylines in Analytics Mode: ${polylinesCount2} (Expected 0)`);
    if (polylinesCount2 !== 0) throw new Error(`Trajectory STILL ON MAP in analytics mode! Found ${polylinesCount2} polylines.`);

    const cleanPath = path.join("/work", "analytics_clean.png");
    await page.screenshot({ path: cleanPath, fullPage: false });
    console.log(`Clean Analytics screenshot saved to: ${cleanPath}`);

    // Test 3: Test Blacklist Dropdown
    console.log("4. Testing Blacklist Alerts dropdown...");
    await page.evaluate(() => {
        toggleBlacklistDropdown();
    });
    await new Promise(r => setTimeout(r, 2000));

    const dropdownState = await page.evaluate(() => {
        const dd = document.getElementById("blacklist-dropdown");
        const list = document.getElementById("blacklist-target-list");
        return {
            isVisible: !dd.classList.contains("hidden"),
            itemsCount: list ? list.children.length : 0,
            text: list ? list.innerText : ""
        };
    });
    console.log(`Blacklist Dropdown open: ${dropdownState.isVisible}, items: ${dropdownState.itemsCount}`);
    if (!dropdownState.isVisible || dropdownState.itemsCount === 0) {
        throw new Error("Blacklist dropdown did not render target items!");
    }

    const ddPath = path.join("/work", "blacklist_dropdown.png");
    await page.screenshot({ path: ddPath, fullPage: false });
    console.log(`Blacklist dropdown screenshot saved to: ${ddPath}`);

    // Test 4: Click a target in the dropdown
    console.log("5. Clicking target DL01AB9999 from dropdown...");
    await page.evaluate(() => {
        selectBlacklistTarget('DL01AB9999');
    });
    await new Promise(r => setTimeout(r, 4000));

    const trackingState = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return {
            mode: currentMode,
            plateInput: document.getElementById("plate-input").value,
            polylines: count
        };
    });
    console.log(`Tracking state after selecting target: mode=${trackingState.mode}, plate=${trackingState.plateInput}, polylines=${trackingState.polylines}`);
    if (trackingState.mode !== 'tracking' || trackingState.polylines === 0) {
        throw new Error("Failed to track target clicked from blacklist dropdown!");
    }

    // Test 5: Switch to Analytics again after tracking DL01AB9999
    console.log("6. Switching to Analytics mode again...");
    await page.evaluate(() => {
        setMode('analytics');
    });
    await new Promise(r => setTimeout(r, 2000));

    let polylinesCount3 = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return count;
    });
    console.log(`Polylines in Analytics Mode second time: ${polylinesCount3} (Expected 0)`);
    if (polylinesCount3 !== 0) throw new Error("Trajectory persisted in analytics mode second time!");

    console.log("ALL VERIFICATION CHECKS PASSED PERFECTLY!");
    await browser.close();
}

test().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});

