#!/usr/bin/env python3
"""Print fixed categories from a private xcresult summary, never raw values."""
import json
from pathlib import Path
import sys


CHECKS = (
    ("UI_REVEAL_INITIAL_START: SCROLL_CONTAINER_NOT_FOUND", "INITIAL_START_SCROLL_CONTAINER_NOT_FOUND"),
    ("UI_REVEAL_INITIAL_SUMMARY: SCROLL_CONTAINER_NOT_FOUND", "INITIAL_SUMMARY_SCROLL_CONTAINER_NOT_FOUND"),
    ("UI_REVEAL_NEXT_START: SCROLL_CONTAINER_NOT_FOUND", "NEXT_START_SCROLL_CONTAINER_NOT_FOUND"),
    ("UI_REVEAL_NEXT_SUMMARY: SCROLL_CONTAINER_NOT_FOUND", "NEXT_SUMMARY_SCROLL_CONTAINER_NOT_FOUND"),
    ("UI_REVEAL_INITIAL_START: CONTROL_NOT_FOUND", "INITIAL_START_CONTROL_NOT_FOUND"),
    ("UI_REVEAL_INITIAL_START: CONTROL_NOT_HITTABLE", "INITIAL_START_CONTROL_NOT_HITTABLE"),
    ("UI_REVEAL_INITIAL_SUMMARY: CONTROL_NOT_FOUND", "INITIAL_SUMMARY_CONTROL_NOT_FOUND"),
    ("UI_REVEAL_INITIAL_SUMMARY: CONTROL_NOT_HITTABLE", "INITIAL_SUMMARY_CONTROL_NOT_HITTABLE"),
    ("UI_REVEAL_NEXT_START: CONTROL_NOT_FOUND", "NEXT_START_CONTROL_NOT_FOUND"),
    ("UI_REVEAL_NEXT_START: CONTROL_NOT_HITTABLE", "NEXT_START_CONTROL_NOT_HITTABLE"),
    ("UI_REVEAL_NEXT_SUMMARY: CONTROL_NOT_FOUND", "NEXT_SUMMARY_CONTROL_NOT_FOUND"),
    ("UI_REVEAL_NEXT_SUMMARY: CONTROL_NOT_HITTABLE", "NEXT_SUMMARY_CONTROL_NOT_HITTABLE"),
    ("新しい探索の検証・書き出し先が以前の記録のまま", "WRONG_SESSION_TARGET"),
    ("以前の記録のサマリーを新しい記録の結果として表示", "STALE_SUMMARY_AFTER_START"),
    ("以前の記録の共有先が残っている", "STALE_EXPORT_AFTER_START"),
    ("選択変更後も別の記録のサマリーが残っている", "STALE_SUMMARY_AFTER_SELECTION"),
    ("選択変更後も別の記録の共有先が残っている", "STALE_EXPORT_AFTER_SELECTION"),
    ("GPX作成後の共有UIがない", "SHARE_CONTROL_NOT_FOUND"),
    ("サマリーを表示できない", "SUMMARY_CONTROL_FAILED"),
    ("別の保存記録へ選択変更できない", "SELECTION_CHANGE_FAILED"),
    ("選択を切り替える別の保存記録がない", "NO_HISTORY_CHOICE"),
    ("記録の選択欄がない", "PICKER_NOT_FOUND"),
    ("探索を開始できない", "SEARCH_START_FAILED"),
    ("探索終了の操作がない", "STOP_CONTROL_NOT_FOUND"),
    ("必要な操作が見つからない", "CONTROL_NOT_FOUND"),
    ("必要な操作を画面に表示できない", "CONTROL_NOT_HITTABLE"),
)


def main():
    try:
        report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        if not isinstance(report, dict) or not isinstance(report.get("testFailures", []), list):
            raise ValueError()
    except (IndexError, OSError, ValueError):
        print("SIMULATOR_REPORT_UNAVAILABLE")
        return
    failures = report.get("testFailures", [])
    if not failures:
        print("SIMULATOR_REPORT_NO_FAILURE_DETAILS")
    for failure in failures:
        message = failure.get("failureText", "") if isinstance(failure, dict) else ""
        if not isinstance(message, str):
            message = ""
        code = next((code for text, code in CHECKS if text in message), "UNCLASSIFIED_ASSERTION")
        print("SIMULATOR_TEST_FAILURE: " + code)


if __name__ == "__main__":
    main()
