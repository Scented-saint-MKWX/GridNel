const puppeteer = require('puppeteer');
const path = require('path');

async function test() {
    console.log("Launching headless browser for Auth & UI Verification...");
    const browser = await puppeteer.launch({
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    console.log("1. Navigating to http://localhost:8000/ ...");
    await page.goto("http://localhost:8000/", { waitUntil: "networkidle0", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));

    // Verify initial state: Public Analytics Mode
    const initialMode = await page.evaluate(() => currentMode);
    console.log(`Initial Mode: ${initialMode} (Expected 'analytics')`);
    if (initialMode !== 'analytics') throw new Error("Default mode should be analytics!");

    // Test 1: Clicking Vehicle Tracking without auth triggers Auth Modal
    console.log("2. Clicking Vehicle Tracking while unauthenticated...");
    await page.evaluate(() => {
        attemptEnterTrackingMode();
    });
    await new Promise(r => setTimeout(r, 1000));

    const isModalOpen = await page.evaluate(() => {
        const m = document.getElementById("auth-modal");
        return !m.classList.contains("hidden");
    });
    console.log(`Auth Modal visible: ${isModalOpen} (Expected true)`);
    if (!isModalOpen) throw new Error("Auth modal did not open when attempting to enter tracking mode!");

    const modalPath = path.join("/work", "auth_modal.png");
    await page.screenshot({ path: modalPath, fullPage: false });
    console.log(`Auth modal screenshot saved to: ${modalPath}`);

    // Test 2: Quick-Fill demo credentials and submit
    console.log("3. Quick-filling credentials and authenticating...");
    await page.evaluate(() => {
        quickFillDemoCredentials();
    });
    await new Promise(r => setTimeout(r, 500));

    await page.evaluate(async () => {
        const fakeEvent = { preventDefault: () => {} };
        await handleAuthSubmit(fakeEvent);
    });
    await new Promise(r => setTimeout(r, 2000));

    const isAuthNow = await page.evaluate(() => {
        const modal = document.getElementById("auth-modal");
        return {
            modalClosed: modal.classList.contains("hidden"),
            isAuth: isAuthorized(),
            mode: currentMode,
            officer: authSession?.operator?.name
        };
    });
    console.log(`Post-login state: modalClosed=${isAuthNow.modalClosed}, isAuth=${isAuthNow.isAuth}, mode=${isAuthNow.mode}, officer="${isAuthNow.officer}"`);
    if (!isAuthNow.isAuth || isAuthNow.mode !== 'tracking') {
        throw new Error("Authentication failed to unlock tracking mode!");
    }

    // Test 3: Track vehicle with auth token
    console.log("4. Tracking MH12AB1284 as authorized officer...");
    await page.evaluate(async () => {
        await trackPlate("MH12AB1284");
    });
    await new Promise(r => setTimeout(r, 4000));

    let polylinesCount = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return count;
    });
    console.log(`Polylines in tracking mode: ${polylinesCount} (Expected >= 1)`);
    if (polylinesCount === 0) throw new Error("Trajectory failed to plot!");

    const trackingPath = path.join("/work", "tracking_authorized.png");
    await page.screenshot({ path: trackingPath, fullPage: false });
    console.log(`Authorized tracking screenshot saved to: ${trackingPath}`);

    // Test 4: Switch to Analytics Mode -> verify trajectory is cleaned up
    console.log("5. Switching back to Analytics Mode...");
    await page.evaluate(() => {
        setMode('analytics');
    });
    await new Promise(r => setTimeout(r, 2000));

    let polylinesCountAnalytics = await page.evaluate(() => {
        let count = 0;
        map.eachLayer(l => {
            if (l instanceof L.Polyline && !(l instanceof L.Polygon)) count++;
        });
        return count;
    });
    console.log(`Polylines in Analytics mode: ${polylinesCountAnalytics} (Expected 0)`);
    if (polylinesCountAnalytics !== 0) throw new Error("Trajectory persisted in analytics mode!");

    // Test 5: Logout operator
    console.log("6. Logging out officer...");
    await page.evaluate(() => {
        logoutOperator();
    });
    await new Promise(r => setTimeout(r, 1000));

    const isLoggedOut = await page.evaluate(() => !isAuthorized() && currentMode === 'analytics');
    console.log(`Logged out successfully: ${isLoggedOut} (Expected true)`);
    if (!isLoggedOut) throw new Error("Logout did not reset state properly!");

    console.log("ALL AUTH & SECURITY TESTS PASSED PERFECTLY!");
    await browser.close();
}

test().catch(err => {
    console.error("Auth test failed:", err);
    process.exit(1);
});

