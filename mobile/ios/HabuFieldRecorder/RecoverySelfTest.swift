#if DEBUG
import Foundation

/// Owner-visible, DEBUG-only storage fault rehearsal.
/// All data is synthetic and isolated from the actual GPS/observation folder.
/// This is NOT evidence that a real on-device storage failure has occurred.
enum RecoverySelfTest {
    static func run() -> String {
        let fileManager = FileManager.default
        let id = UUID().uuidString
        let root = fileManager.temporaryDirectory
            .appendingPathComponent("habu-debug-recovery-" + id, isDirectory: true)
        let suite = "org.habuai.debug-recovery." + id
        guard let prefs = UserDefaults(suiteName: suite) else {
            return "FAIL: テスト専用設定を作成できません"
        }
        defer {
            prefs.removePersistentDomain(forName: suite)
            try? fileManager.removeItem(at: root)
        }
        do {
            try fileManager.createDirectory(at: root, withIntermediateDirectories: true)
            let failed = TrackStore(
                rootDirectory: root,
                preferences: prefs,
                beforePersistActiveMarker: { throw TrackStoreError.cannotWrite }
            )
            do {
                _ = try failed.start()
                return "FAIL: 保存失敗が検出されませんでした"
            } catch TrackStoreError.cannotWrite {
                // Expected injected interruption after the START line is stored.
            }
            guard failed.activeId == nil,
                  let orphan = failed.allSessionIds().onlyElement else {
                return "FAIL: 保存失敗後に孤立原本を発見できません"
            }
            let original = root.appendingPathComponent(orphan + ".jsonl")
            let before = try Data(contentsOf: original)
            guard !before.isEmpty else { return "FAIL: 原本が空です" }

            // Construct a new store, equivalent to reloading persisted state.
            let reopened = TrackStore(rootDirectory: root, preferences: prefs)
            guard reopened.activeId == nil,
                  reopened.recoveryCandidates().contains(orphan) else {
                return "FAIL: 再起動相当の復旧候補検出に失敗"
            }
            let exported = try reopened.exportedRecoveryFile(id: orphan)
            guard try Data(contentsOf: exported) == before,
                  try Data(contentsOf: original) == before else {
                return "FAIL: 原本バックアップの内容が一致しません"
            }
            let newSession = try reopened.start()
            guard newSession != orphan else {
                return "FAIL: 過去の孤立原本を再使用しました"
            }
            try reopened.stop()
            return "PASS: 疑似保存失敗→孤立原本検出→原本一致→別セッション開始"
        } catch {
            return "FAIL: 隔離復旧試験でエラー（\(type(of: error))）"
        }
    }
}

private extension Array {
    var onlyElement: Element? {
        count == 1 ? first : nil
    }
}
#endif
