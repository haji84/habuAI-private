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

    private let manager = CLLocationManager()
    private let store = TrackStore()
    private var pendingUserStart = false

    var latestSessionId: String? { store.latestId }

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = 5
        manager.activityType = .fitness
        manager.pausesLocationUpdatesAutomatically = false
        manager.showsBackgroundLocationIndicator = true
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
            let id = try store.start()
            guard UUID(uuidString: id) != nil else { throw TrackStoreError.invalidSession }
            // Must have the background location capability in Info.plist.
            manager.allowsBackgroundLocationUpdates = true
            manager.startUpdatingLocation()
            pendingUserStart = false
            isTracking = true
            status = "GPS記録中（画面ロック中も継続可能）"
        } catch {
            pendingUserStart = false
            status = "端末内保存を開始できません: \(error.localizedDescription)"
        }
    }
    func finish() {
        manager.stopUpdatingLocation()
        manager.allowsBackgroundLocationUpdates = false
        pendingUserStart = false
        isTracking = false
        do {
            try store.stop()
            status = "探索終了。GPXまたは元記録を端末に書き出せます。"
        } catch {
            status = "探索終了時の保存エラー: \(error.localizedDescription)"
        }
    }
    func addObservation(type: String, species: String, number: Int) {
        guard let id = store.activeId else { status = "探索開始が必要です"; return }
        guard ["capture", "sighting", "roadkill", "other"].contains(type),
              !species.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              number >= 1 && number <= 100 else {
            status = "記録の種類または匹数が不正です"
            return
        }
        do {
            try store.append(id: id, record: TrackRecord(
                kind: "event", time: Date().timeIntervalSince1970,
                id: UUID().uuidString, type: type, species: String(species.prefix(80)),
                count: number
            ))
            status = "観察 \(number)匹を端末内に保存。確定捕獲には未反映。"
        } catch { status = "観察を保存できません: \(error.localizedDescription)" }
    }
    func export(_ ext: String) -> URL? {
        guard let id = store.latestId else { status = "探索記録がありません"; return nil }
        do { return try store.exportedFile(id: id, ext: ext) }
        catch { status = "エクスポート失敗: \(error.localizedDescription)"; return nil }
    }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse: beginIfPermitted()
        case .denied, .restricted:
            manager.stopUpdatingLocation()
            isTracking = false
            pendingUserStart = false
            status = "位置情報が許可されていません。測位停止。"
        default: break
        }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations updates: [CLLocation]) {
        guard let id = store.activeId, isTracking else { return }
        for p in updates where p.horizontalAccuracy >= 0 &&
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
