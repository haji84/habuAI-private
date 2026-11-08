import CoreLocation
import Foundation
import SwiftUI

/**
 * Owner-initiated tracking, configured with Background Modes > Location.
 * Screen lock and switching apps can continue while Core Location runs.
 * User force-quit, permission revocation, OS termination or missing GNSS fixes
 * are NOT bypassed or misrepresented as a complete route.
 */
final class BackgroundTrackRecorder: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published private(set) var status = "停止中"
    @Published private(set) var count = 0
    @Published private(set) var isTracking = false
    @Published private(set) var lastFixAt: Date?
    @Published private(set) var recoveryCandidates: [String] = []
    @Published private(set) var availableSessionIds: [String] = []

    private let manager = CLLocationManager()
    private let store = TrackStore()
    private var pendingUserStart = false
    private var measurementStartedAt: Date?

    var latestSessionId: String? { store.latestId }
    // After an interrupted marker write, latestId can still name an older
    // completed search. Evidence/export must follow the actual recording.
    var activeSessionId: String? { store.activeId }
    // A recovered unfinished log can be closed without turning GPS back on.
    var hasUnfinishedSession: Bool { store.activeId != nil }

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = 5
        manager.activityType = .fitness
        manager.pausesLocationUpdatesAutomatically = false
        manager.showsBackgroundLocationIndicator = true
        recoveryCandidates = store.recoveryCandidates()
        availableSessionIds = store.allSessionIds()
        if store.activeId != nil { status = "前回の探索は未終了。GPSは明示的に再開してください。" }
    }
    func requestStart() {
        pendingUserStart = true
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse: beginIfPermitted()
        case .notDetermined: manager.requestWhenInUseAuthorization()
        default:
            pendingUserStart = false
            status = "位置情報を許可してください。拒否中は測位できません。"
        }
    }
    private func beginIfPermitted() {
        guard pendingUserStart else { return }
        guard CLLocationManager.locationServicesEnabled() else {
            pendingUserStart = false
            status = "端末の位置情報が無効です。"
            return
        }
        do {
            let priorSessionId = store.activeId
            let id = try store.start()
            guard UUID(uuidString: id) != nil else { throw TrackStoreError.invalidSession }
            let resumingUnfinishedSession = priorSessionId == id
            if resumingUnfinishedSession {
                // The app was restarted. Preserve the prior session without
                // inventing GPS points across the unobserved interruption.
                try store.append(id: id, record: TrackRecord(
                    kind: "gap", time: Date().timeIntervalSince1970,
                    note: "explicit-user-restart"
                ))
            }
            // Must have the background location capability in Info.plist.
            measurementStartedAt = Date()
            manager.allowsBackgroundLocationUpdates = true
            manager.startUpdatingLocation()
            pendingUserStart = false
            isTracking = true
            count = 0
            lastFixAt = nil
            availableSessionIds = store.allSessionIds()
            status = manager.accuracyAuthorization == .reducedAccuracy
                ? "概算位置が有効です。設定で「正確な位置情報」を有効化してください。測位点は精度付きで保存します。"
                : "GPS測位を開始しました。初回の実測点を待っています。"
        } catch {
            pendingUserStart = false
            status = "端末内保存を開始できません: \(error.localizedDescription)"
        }
    }
    func finish() {
        manager.stopUpdatingLocation()
        manager.allowsBackgroundLocationUpdates = false
        measurementStartedAt = nil
        pendingUserStart = false
        isTracking = false
        do {
            try store.stop()
            recoveryCandidates = store.recoveryCandidates()
            availableSessionIds = store.allSessionIds()
            status = "探索終了。GPXまたは元記録を端末に書き出せます。"
        } catch {
            status = "探索終了時の保存エラー: \(error.localizedDescription)"
        }
    }
    func addObservation(type: String, species: String, number: Int, owner: String? = nil, note: String? = nil) {
        guard let id = store.activeId else { status = "探索開始が必要です"; return }
        guard ["capture", "sighting", "roadkill", "other"].contains(type),
              !species.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              number >= 1 && number <= 100,
              owner == nil || owner == "self" || owner == "other" else {
            status = "記録の種類または匹数が不正です"
            return
        }
        do {
            try store.append(id: id, record: TrackRecord(
                kind: "event", time: Date().timeIntervalSince1970,
                id: UUID().uuidString, type: type, species: String(species.prefix(80)),
                count: number,
                note: note.map { String($0.prefix(300)) },
                owner: owner
            ))
            status = "観察 \(number)匹を端末内に保存。確定捕獲には未反映。"
        } catch { status = "観察を保存できません: \(error.localizedDescription)" }
    }
    func export(_ ext: String, sessionId: String? = nil) -> URL? {
        let id = sessionId ?? store.latestId
        guard let id, store.allSessionIds().contains(id) else {
            status = "探索記録がありません"
            return nil
        }
        do { return try store.exportedFile(id: id, ext: ext) }
        catch { status = "エクスポート失敗: \(error.localizedDescription)"; return nil }
    }
    func evidenceSummary(_ id: String) -> String {
        guard store.allSessionIds().contains(id) else { return "探索記録がありません" }
        do { return try store.evidence(id: id).displayText }
        catch { return "サマリーを作成できません。原本保持。詳細: \(error.localizedDescription)" }
    }

    func exportRecovery(_ id: String) -> URL? {
        do { return try store.exportedRecoveryFile(id: id) }
        catch {
            status = "復旧用原本の保存に失敗: \(error.localizedDescription)"
            return nil
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse: beginIfPermitted()
        case .denied, .restricted:
            manager.stopUpdatingLocation()
            manager.allowsBackgroundLocationUpdates = false
            measurementStartedAt = nil
            isTracking = false
            pendingUserStart = false
            if let id = store.activeId {
                try? store.append(id: id, record: TrackRecord(
                    kind: "gap", time: Date().timeIntervalSince1970,
                    note: "location-permission-revoked"
                ))
            }
            status = "位置情報が許可されていません。測位停止。"
        default: break
        }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations updates: [CLLocation]) {
        guard let id = store.activeId, isTracking else { return }
        // Core Location may deliver cached points when updates begin. Never
        // attribute a pre-start position to the current owner-initiated run.
        let earliest = measurementStartedAt?.addingTimeInterval(-5) ?? .distantPast
        let latest = Date().addingTimeInterval(60)
        for p in updates where p.timestamp >= earliest && p.timestamp <= latest &&
            p.horizontalAccuracy >= 0 &&
            p.coordinate.latitude.isFinite && p.coordinate.longitude.isFinite {
            guard abs(p.coordinate.latitude) <= 90, abs(p.coordinate.longitude) <= 180 else { continue }
            do {
                try store.append(id: id, record: TrackRecord(
                    kind: "fix", time: p.timestamp.timeIntervalSince1970,
                    latitude: p.coordinate.latitude, longitude: p.coordinate.longitude,
                    accuracy: p.horizontalAccuracy,
                    altitude: p.verticalAccuracy >= 0 ? p.altitude : nil
                ))
                count += 1
                lastFixAt = p.timestamp
                status = "実測GPSを保存中（画面ロック中も継続可能）"
            } catch {
                manager.stopUpdatingLocation()
                isTracking = false
                status = "GPS保存に失敗。測位停止: \(error.localizedDescription)"
                return
            }
        }
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if let id = store.activeId {
            try? store.append(id: id, record: TrackRecord(kind: "gap", time: Date().timeIntervalSince1970,
                                                         note: "GPS error: \(error.localizedDescription)"))
        }
        status = "GPSに中断の可能性: \(error.localizedDescription)"
    }
}
