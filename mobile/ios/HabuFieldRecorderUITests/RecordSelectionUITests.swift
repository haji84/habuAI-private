import XCTest

/// Runs only in the isolated Simulator; never reads an owner's GPS records.
final class RecordSelectionUITests: XCTestCase {
    private enum RevealContext: String {
        case initialStart = "INITIAL_START"
        case initialSummary = "INITIAL_SUMMARY"
        case nextStart = "NEXT_START"
        case nextSummary = "NEXT_SUMMARY"
    }

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
    }

    func testNewSearchSelectsNewRecordAndClearsPreviousEvidenceAndExport() {
        let app = XCUIApplication()
        app.launch()
        startSearch(app, context: .initialStart)
        app.buttons["探索終了"].tap()

        let summaryButton = app.buttons["showRecordEvidence"]
        reveal(summaryButton, in: app, scrollingUp: true, context: .initialSummary)
        summaryButton.tap()
        XCTAssertTrue(app.staticTexts["recordEvidenceText"].waitForExistence(timeout: 5), "サマリーを表示できない")
        let previousSelection = selectionLabel(in: app)

        app.buttons["GPXを作成"].tap()
        let share = app.buttons["ファイルを保存・共有"]
        XCTAssertTrue(share.waitForExistence(timeout: 5), "GPX作成後の共有UIがない")

        // The second search must become the target of evidence and export,
        // even though the first retained session is still available.
        startSearch(app, context: .nextStart)
        app.buttons["探索終了"].tap()
        reveal(summaryButton, in: app, scrollingUp: true, context: .nextSummary)
        XCTAssertNotEqual(selectionLabel(in: app), previousSelection,
                          "新しい探索の検証・書き出し先が以前の記録のまま")
        XCTAssertFalse(app.staticTexts["recordEvidenceText"].exists,
                       "以前の記録のサマリーを新しい記録の結果として表示している")
        XCTAssertFalse(share.exists, "以前の記録の共有先が残っている")

        summaryButton.tap()
        XCTAssertTrue(app.staticTexts["recordEvidenceText"].waitForExistence(timeout: 5), "サマリーを表示できない")
    }

    func testSelectingAnotherRecordClearsPreviousEvidenceAndExport() {
        let app = XCUIApplication()
        app.launch()
        startSearch(app, context: .initialStart)
        app.buttons["探索終了"].tap()
        startSearch(app, context: .nextStart)
        app.buttons["探索終了"].tap()

        let summaryButton = app.buttons["showRecordEvidence"]
        reveal(summaryButton, in: app, scrollingUp: true, context: .initialSummary)
        summaryButton.tap()
        XCTAssertTrue(app.staticTexts["recordEvidenceText"].waitForExistence(timeout: 5), "サマリーを表示できない")
        app.buttons["GPXを作成"].tap()
        let share = app.buttons["ファイルを保存・共有"]
        XCTAssertTrue(share.waitForExistence(timeout: 5), "GPX作成後の共有UIがない")

        let previousSelection = selectionLabel(in: app)
        sessionPicker(in: app).tap()
        let choices = app.buttons.matching(NSPredicate(
            format: "label BEGINSWITH %@", "探索 "
        )).allElementsBoundByIndex
        guard let other = choices.first(where: { !previousSelection.contains($0.label) }) else {
            XCTFail("選択を切り替える別の保存記録がない")
            return
        }
        other.tap()
        XCTAssertNotEqual(selectionLabel(in: app), previousSelection, "別の保存記録へ選択変更できない")
        XCTAssertFalse(app.staticTexts["recordEvidenceText"].exists,
                       "選択変更後も別の記録のサマリーが残っている")
        XCTAssertFalse(share.exists, "選択変更後も別の記録の共有先が残っている")
    }

    private func startSearch(_ app: XCUIApplication, context: RevealContext) {
        let start = app.buttons["探索開始"]
        reveal(start, in: app, scrollingUp: false, context: context)
        start.tap()
        let alert = XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.firstMatch
        if alert.waitForExistence(timeout: 3) {
            for label in ["Allow While Using App", "While Using the App", "Allow Once",
                          "アプリの使用中は許可", "1度だけ許可", "一度だけ許可"] {
                if alert.buttons[label].exists {
                    alert.buttons[label].tap()
                    break
                }
            }
        }
        let stopped = app.buttons["探索終了"]
        XCTAssertTrue(stopped.waitForExistence(timeout: 10), "探索終了の操作がない")
        XCTAssertTrue(stopped.isEnabled, "探索を開始できない")
    }

    private func selectionLabel(in app: XCUIApplication) -> String {
        let picker = sessionPicker(in: app)
        return picker.label + " " + (picker.value as? String ?? "")
    }

    private func sessionPicker(in app: XCUIApplication) -> XCUIElement {
        let picker = app.buttons.matching(NSPredicate(
            format: "label BEGINSWITH %@ OR label BEGINSWITH %@",
            "探索 ", "書き出す探索記録"
        )).firstMatch
        XCTAssertTrue(picker.exists, "記録の選択欄がない")
        return picker
    }

    private func reveal(_ element: XCUIElement, in app: XCUIApplication, scrollingUp: Bool,
                        context: RevealContext) {
        XCTAssertTrue(element.waitForExistence(timeout: 15),
                      "UI_REVEAL_\(context.rawValue): CONTROL_NOT_FOUND")
        let scrollView = app.scrollViews.firstMatch
        XCTAssertTrue(scrollView.exists,
                      "UI_REVEAL_\(context.rawValue): SCROLL_CONTAINER_NOT_FOUND")
        for _ in 0..<6 {
            if element.isHittable { return }
            if scrollingUp { scrollView.swipeUp() } else { scrollView.swipeDown() }
        }
        XCTAssertTrue(element.isHittable,
                      "UI_REVEAL_\(context.rawValue): CONTROL_NOT_HITTABLE")
    }
}
