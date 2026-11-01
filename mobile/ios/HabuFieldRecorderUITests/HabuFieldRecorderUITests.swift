import XCTest

/// Simulator-only synthetic GPS acceptance. These tests must never be
/// interpreted as proof of on-device locked-screen collection.
final class HabuFieldRecorderUITests: XCTestCase {
    override func setUp() {
        super.setUp()
        continueAfterFailure = false
    }

    func testSyntheticLocationCaptureAndGPXExport() {
        let app = XCUIApplication()
        app.launch()

        let start = app.buttons["探索開始"]
        XCTAssertTrue(start.waitForExistence(timeout: 30), "探索開始ボタンを表示できない")
        start.tap()

        // On a clean Simulator Core Location may ask for explicit permission.
        // Prefer a user-facing authorization flow; do not alter production code.
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let permission = springboard.alerts.firstMatch
        if permission.waitForExistence(timeout: 5) {
            let buttons = permission.buttons
            let labels = [
                "Allow While Using App",
                "While Using the App",
                "Allow Once",
                "アプリの使用中は許可",
                "1度だけ許可",
                "一度だけ許可"
            ]
            for label in labels {
                if buttons[label].exists {
                    buttons[label].tap()
                    break
                }
            }
        }

        // A separate CI loop injects moving, artificial positions through
        // simctl. No owner's original GPS file or location is involved.
        let indicator = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "この起動で保存した実測GPS:")
        ).firstMatch
        XCTAssertTrue(indicator.waitForExistence(timeout: 30), "GPS点数の表示がない")
        let deadline = Date().addingTimeInterval(65)
        var fixes = 0
        repeat {
            let label = indicator.label
            if let tail = label.components(separatedBy: "実測GPS:").last,
               let count = Int(tail.components(separatedBy: "点").first?
                    .trimmingCharacters(in: .whitespacesAndNewlines) ?? "") {
                fixes = count
            }
            if fixes > 0 { break }
            Thread.sleep(forTimeInterval: 2)
        } while Date() < deadline
        XCTAssertGreaterThan(fixes, 0, "模擬位置を取得・保存できていない")

        // Record a synthetic observation, then stop the local session.
        let save = app.buttons["端末内に観察を保存"]
        if !save.isHittable { app.swipeUp() }
        XCTAssertTrue(save.waitForExistence(timeout: 10), "観察保存ボタンがない")
        save.tap()
        let stop = app.buttons["探索終了"]
        if !stop.isHittable { app.swipeDown() }
        XCTAssertTrue(stop.waitForExistence(timeout: 10), "探索終了ボタンがない")
        stop.tap()

        let gpx = app.buttons["GPXを作成"]
        if !gpx.isHittable { app.swipeUp() }
        XCTAssertTrue(gpx.waitForExistence(timeout: 10), "GPX生成ボタンがない")
        gpx.tap()
        let share = app.descendants(matching: .any).matching(
            NSPredicate(format: "label == %@", "ファイルを保存・共有")
        ).firstMatch
        XCTAssertTrue(share.waitForExistence(timeout: 15), "GPX生成後のファイル共有UIがない")
        // Do not open the share sheet: privacy contract requires local-only.
    }
}
