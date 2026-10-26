import SwiftUI

struct ContentView: View {
    @ObservedObject var recorder: BackgroundTrackRecorder
    @State private var species = "ハブ"
    @State private var quantity = "1"
    @State private var category = "捕獲"
    @State private var exported: URL?

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
                    Text("取得した実測GPS: \(recorder.count)点")
                        .font(.headline)
                    HStack {
                        Button("探索開始") { recorder.requestStart() }
                            .disabled(recorder.isTracking)
                        Button("探索終了") { recorder.finish() }
                            .disabled(!recorder.isTracking)
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
                    HStack {
                        Button("GPXを作成") { exported = recorder.export("gpx") }
                        Button("元ログJSONL") { exported = recorder.export("jsonl") }
                    }.buttonStyle(.bordered)
                    if let exported {
                        ShareLink(item: exported) { Label("ファイルを保存・共有", systemImage: "square.and.arrow.up") }
                    }
                    Text("記録は端末内のみ。取得した座標は送信しません。日別確定集計への反映は既存記録との重複確認が必要です。")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("HABU FIELD")
        }
    }
}
