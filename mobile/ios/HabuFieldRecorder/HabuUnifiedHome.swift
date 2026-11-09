import SwiftUI
import WebKit

/// One native application, one unchanged GPS writer. The prediction and
/// dashboard tabs must never silently turn an unreviewed field event into an
/// official model label or approved historical count.
struct HabuUnifiedHome: View {
    @ObservedObject var recorder: BackgroundTrackRecorder
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TabView {
            ContentView(recorder: recorder)
                .tabItem { Label("探索", systemImage: "location.north.circle") }
                .accessibilityIdentifier("fieldTab")

            HabuAIHome(recorder: recorder)
                .tabItem { Label("ハブAI", systemImage: "brain.head.profile") }
                .accessibilityIdentifier("habuAITab")

            HabuLocalDashboard(recorder: recorder)
                .tabItem { Label("ダッシュボード", systemImage: "chart.bar.xaxis") }
                .accessibilityIdentifier("dashboardTab")
        }
        .onChange(of: scenePhase) { phase in
            // Resume pending File Provider writes when the owner reopens the
            // application. iOS/Drive remote delivery is never assumed here.
            if phase == .active { recorder.retryPendingInbox() }
        }
    }
}

private struct HabuAIHome: View {
    @ObservedObject var recorder: BackgroundTrackRecorder

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Label("ハブAI", systemImage: "brain.head.profile")
                        .font(.title.bold())
                    Text("予測・探索・学習を同じアプリで扱うための入口")
                        .foregroundStyle(.secondary)
                    GroupBox("公式予測 P0 / P1") {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("公式予測のアプリ内受信は未接続", systemImage: "exclamationmark.circle")
                                .font(.headline)
                            Text("既存モデルの推論、事前時刻の証明、Freeze、版とSHAの検証が済んだ予測だけを表示します。手作りの予測を公式扱いにはしません。")
                            Text("今夜の位置・ルート・捕獲見込み：未取得")
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    GroupBox("探索記録から学習へ") {
                        VStack(alignment: .leading, spacing: 10) {
                            Label("1. GPS探索・本人捕獲・目撃を端末保存", systemImage: "checkmark.circle")
                            Label("2. 探索終了後、暗号化して選択フォルダへ書込み", systemImage: "lock.shield")
                            Label("3. 原本の独立受信・重複照合・適格性判定", systemImage: "checkmark.shield")
                            Label("4. 学習・公式ダッシュボードへの反映", systemImage: "chart.line.uptrend.xyaxis")
                            Text("3と4のクラウド側の自動接続は未実証。GPS軌跡だけでハブ不在データを作りません。")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    Text(recorder.inboxStatus)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("ハブAI")
        }
    }
}

private struct HabuLocalDashboard: View {
    @ObservedObject var recorder: BackgroundTrackRecorder
    @State private var summary = HabuLocalSummary()
    @State private var showPrivateDashboard = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("このiPhoneの探索記録")
                        .font(.title2.bold())
                    Text("端末原本から計算した未照合の速報値。既存ダッシュボードの確定捕獲数には自動加算しません。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    HStack(spacing: 12) {
                        statistic("本人ハブ捕獲", summary.ownerHabuCaptures, "匹・未確定")
                        statistic("完了探索", summary.completedSessions, "回・端末記録")
                    }
                    HStack(spacing: 12) {
                        statistic("ハブ目撃", summary.habuSightings, "匹")
                        statistic("その他目撃", summary.wildlifeSightings, "匹")
                    }
                    GroupBox("原本と同期状態") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("実測GPS: \(summary.gpsFixes)点")
                            Text("未終了: \(summary.unfinishedSessions)件")
                            Text("保留原本: \(summary.heldSessions)件")
                            Text("その他・未確認イベント: \(summary.heldEvents)件")
                            Text(recorder.inboxStatus)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            Text("Google Driveへの実到着・復元は、受信側で独立確認するまで未確認です。")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    Button("端末内の集計を更新") { reload() }
                        .buttonStyle(.bordered)
                    if !summary.nights.isEmpty {
                        Text("探索夜別（07:00 JST区切り）")
                            .font(.headline)
                        ForEach(summary.nights) { night in
                            HStack {
                                Text(night.id).font(.subheadline.monospacedDigit())
                                Spacer()
                                Text("捕獲 \(night.captures) / ハブ目撃 \(night.habuSightings) / その他 \(night.wildlifeSightings)")
                                    .font(.footnote)
                            }
                            Divider()
                        }
                    }
                    Divider()
                    Button {
                        showPrivateDashboard = true
                    } label: {
                        Label("既存の確定ダッシュボードをアプリ内で開く",
                              systemImage: "chart.bar.doc.horizontal")
                    }
                    .buttonStyle(.borderedProminent)
                    Text("既存サイトはアクセス制限付きの別データ。ログインが必要です。この操作では端末のGPS原本をWeb画面へ渡しません。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("ダッシュボード")
            .onAppear(perform: reload)
            .onChange(of: recorder.isTracking) { tracking in
                if !tracking { reload() }
            }
            .sheet(isPresented: $showPrivateDashboard) {
                NavigationStack {
                    OwnerDashboardWebView()
                        .navigationTitle("確定ダッシュボード")
                        .navigationBarTitleDisplayMode(.inline)
                        .toolbar {
                            ToolbarItem(placement: .confirmationAction) {
                                Button("閉じる") { showPrivateDashboard = false }
                            }
                        }
                }
            }
        }
    }

    private func reload() {
        summary = HabuLocalSummary.from(store: TrackStore())
    }

    private func statistic(_ heading: String, _ value: Int, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(heading).font(.footnote)
            Text(value, format: .number).font(.title.bold()).monospacedDigit()
            Text(detail).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

/// Read-only navigation to the already existing protected historic dashboard.
/// No JavaScript/native bridge, local file permissions, or raw-session transfer.
private struct OwnerDashboardWebView: UIViewRepresentable {
    private let url = URL(string: "https://hub-natural-private.pages.dev/")!

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: config)
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        return view
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
