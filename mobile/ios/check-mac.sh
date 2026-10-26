#!/bin/zsh
# HABU FIELD local Mac smoke build. Requires Xcode (Mac) and XcodeGen.
# This does not publish, sign for distribution, or upload GPS.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "STOP: Macで実行してください。"
  exit 2
fi
if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "STOP: XcodeをApp Storeからインストールし、最初に起動してください。"
  exit 2
fi
if ! xcodebuild -version; then
  echo "STOP: Xcodeの設定が未完了です。Xcodeを起動して利用規約を確認してください。"
  exit 2
fi
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "STOP: XcodeGenが必要です。Homebrew導入済みなら brew install xcodegen"
  exit 2
fi
HERE="${0:A:h}"
cd "$HERE"
xcodegen generate --spec project.yml
echo "Xcodeプロジェクト生成: $PWD/HabuFieldRecorder.xcodeproj"
echo "Info.plist バックグラウンド位置情報:"
/usr/libexec/PlistBuddy -c 'Print :UIBackgroundModes' HabuFieldRecorder/Info.plist
echo "iOS Simulator向け署名不要ビルドを開始 (実機GPS検証ではありません)"
xcodebuild -project HabuFieldRecorder.xcodeproj \
  -scheme HabuFieldRecorder -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO -quiet build
echo "SIMULATOR_BUILD_PASS: 次はXcodeでApple IDを設定し実機インストールしてください。"
