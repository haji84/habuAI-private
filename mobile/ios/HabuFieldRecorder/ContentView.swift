import SwiftUI

struct ContentView: View {
    @ObservedObject var recorder: BackgroundTrackRecorder
    @State private var species = "ハブ"
    @State private var quantity = "1"
    @State private var category = "捕獲"
    @State private var exported: URL?
    @State private var selectedSessionId = ""
    @State private var recordEvidenceText = ""
    #if DEBUG
    @State private var recoverySelfTestResult = ""
    #endif

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("GPSをロック中も記録")
                        .font(.title2.bold())
                    Text("探索開始後は画面を閉じてもバックグラウンド位置情報を受信できます。端末強制終了、GPS無効、OS制限時は保証できません。")
                        .font(.footnote)
                    Text(recorder.status)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("trackerStatus")
                    Text("この起動で保存した実測GPS: \(recorder.count)点")
                        .font(.headline)
                    if let last = recorder.lastFixAt {
                        Text("直近の実測: \(last.formatted(date: .abbreviated, time: .standard))")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    if !recorder.isTracking && recorder.hasUnfinishedSession {
                        Text("未終了の探索記録があります。記録を明示的に再開するか、探索終了で閉じてください。")
                            .font(.footnote)
                    }
                    HStack {
                        Button("探索開始") { recorder.requestStart() }
                            .disabled(recorder.isTracking)
                        Button("探索終了") { recorder.finish() }
                            .disabled(!recorder.hasUnfinishedSession)
                    }
                    .buttonStyle(.borderedProminent)
                    Divider()
                    Text("捕獲・目撃の記録").font(.headline)
                    Picker("記録種別", selection: $category) {
                        ForEach(["捕獲", "目撃", "轢死", "その他"], id: \.self) { Text($0) }
                    }.pickerStyle(.segmented)
                    TextField("生き物の種類", text: $species)
                        .textFieldStyle(.roundedBorder)
                    TextField("匹数（整数）", text: $quantity)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                    Button("端末内に観察を保存") {
                        let types = ["捕獲": "capture", "目撃": "sighting",
                                     "轢死": "roadkill", "その他": "other"]
                        recorder.addObservation(
                            type: types[category] ?? "other",
                            species: species,
                            number: Int(quantity) ?? -1
                        )
                    }.disabled(!recorder.isTracking)
                    Divider()
                    Text("GPX・原記録の出力").font(.headline)
                    if !recorder.recoveryCandidates.isEmpty {
                        Text("前回の保存途中で残った記録が見つかりました。自動再開せず、選択した原本を端末へ保存できます。")
                            .font(.footnote)
                        ForEach(recorder.recoveryCandidates, id: \.self) { id in
                            Button("復旧用原本を保存: \(String(id.prefix(8)))") {
                                exported = recorder.exportRecovery(id)
                            }
                        }
                        Text("復旧原本には正確な位置情報が含まれます。公開共有先に保存しないでください。")
                            .font(.footnote)
                    }
                    if !recorder.availableSessionIds.isEmpty {
                        Picker("書き出す探索記録", selection: $selectedSessionId) {
                            ForEach(recorder.availableSessionIds, id: \.self) { id in
                                Text("探索 \(String(id.prefix(8)))").tag(id)
                            }
                        }
                        HStack {
                            Button("GPXを作成") {
                                exported = recorder.export("gpx", sessionId: selectedSessionId)
                            }
                            Button("元ログJSONL") {
                                exported = recorder.export("jsonl", sessionId: selectedSessionId)
                            }
                            Button("原本そのまま") {
                                exported = recorder.export("raw", sessionId: selectedSessionId)
                            }
                        }.buttonStyle(.bordered)
                        Button("記録の検証サマリーを表示") {
                            recordEvidenceText = recorder.evidenceSummary(selectedSessionId)
                        }
                        .accessibilityIdentifier("showRecordEvidence")
                    }
                    if !recordEvidenceText.isEmpty {
                        Text(recordEvidenceText)
                            .font(.footnote)
                            .accessibilityIdentifier("recordEvidenceText")
                    }
                    if let exported {
                        ShareLink(item: exported) { Label("ファイルを保存・共有", systemImage: "square.and.arrow.up") }
                    }
                    Text("記録は端末内のみ。取得した座標は送信しません。日別確定集計への反映は既存記録との重複確認が必要です。")
                        .font(.footnote).foregroundStyle(.secondary)
                    #if DEBUG
                    Divider()
                    Text("開発用・保存失敗復旧試験")
                        .font(.headline)
                    Text("GPS原本とは別の隔離フォルダで疑似保存失敗を起こし、原本保持と復旧を診断します。実際の位置情報や捕獲統計は変更しません。")
                        .font(.footnote).foregroundStyle(.secondary)
                    Button("保存失敗→復旧を自己診断") {
                        recoverySelfTestResult = RecoverySelfTest.run()
                    }
                    .accessibilityIdentifier("runRecoverySelfTest")
                    if !recoverySelfTestResult.isEmpty {
                        Text(recoverySelfTestResult)
                            .font(.footnote)
                            .accessibilityIdentifier("recoverySelfTestResult")
                    }
                    #endif
                }
                .padding()
            }
            .navigationTitle("HABU FIELD")
            .onAppear {
                if selectedSessionId.isEmpty {
                    selectedSessionId = recorder.availableSessionIds.first ?? ""
                }
            }
            .onChange(of: recorder.availableSessionIds) { ids in
                if !ids.contains(selectedSessionId) {
                    selectedSessionId = ids.first ?? ""
                }
            }
        }
    }
}
