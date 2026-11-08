import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @ObservedObject var recorder: BackgroundTrackRecorder
    @State private var species = "ハブ"
    @State private var quantity = "1"
    @State private var category = "捕獲"
    @State private var observationOwner = "unknown"
    @State private var observationNote = ""
    @State private var wildlifeMode = "目撃"
    @State private var measuredAirTemperature = ""
    @State private var conditionFeedback = ""
    @State private var backupPassphrase = ""
    @State private var backupConfirmation = ""
    @State private var sealedBackup: URL?
    @State private var backupMessage = ""
    @State private var showEncryptedBackupPicker = false
    @State private var showInboxFolderPicker = false
    @State private var exportedFiles: [URL] = []
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
                    Text("現場クイック記録").font(.headline)
                    Text("安全に停車して操作。1タップで時刻付きの観察を同じGPS探索原本へ保存します。")
                        .font(.footnote).foregroundStyle(.secondary)
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        Button("🐍 本人ハブ捕獲 ＋1") {
                            recorder.addObservation(type: "capture", species: "ハブ", number: 1, owner: "self")
                        }
                        .accessibilityIdentifier("quickSelfHabuCapture")
                        Button("👁 ハブ目撃 ＋1") {
                            recorder.addObservation(type: "sighting", species: "ハブ", number: 1, owner: "self")
                        }
                        .accessibilityIdentifier("quickHabuSighting")
                        Button("⚠️ ハブ轢死 ＋1") {
                            recorder.addObservation(type: "roadkill", species: "ハブ", number: 1, owner: "self")
                        }
                        Button("↪ ハブ取り逃し ＋1") {
                            recorder.addObservation(type: "other", species: "ハブ", number: 1, owner: "self",
                                                    note: "取り逃し")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(!recorder.isTracking)
                    DisclosureGroup("ほかの生き物の目撃・轢死") {
                        Text("先に記録種別を選び、生き物の名前をタップ。本人のハブ捕獲数には加算しません。")
                            .font(.footnote)
                        Picker("ほかの生き物の記録種別", selection: $wildlifeMode) {
                            Text("目撃").tag("目撃")
                            Text("轢死").tag("轢死")
                        }
                        .pickerStyle(.segmented)
                        .accessibilityIdentifier("wildlifeObservationMode")
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            ForEach([
                                "クロウサギ", "ヤマシギ", "ネズミ", "アカマタ", "ヒメハブ",
                                "ガラスヒバ", "リュウキュウアオバズク", "オットンガエル",
                                "シラガケナガネズミ", "リュウキュウアオヘビ"
                            ], id: \.self) { animal in
                                Button(animal) {
                                    recorder.addObservation(type: wildlifeMode == "目撃" ? "sighting" : "roadkill",
                                                            species: animal, number: 1, owner: "self")
                                }
                                .buttonStyle(.borderedProminent)
                                .controlSize(.large)
                                .disabled(!recorder.isTracking)
                            }
                        }
                        Text("一覧にない種類、複数匹、詳しい状況は下の詳細入力から保存できます。")
                            .font(.footnote)
                    }
                    DisclosureGroup("路面・天気・実測気温（必要なときだけ）") {
                        Text("路面と天気はその場で確認。変わったときだけ再記録します。")
                            .font(.footnote)
                        Text("路面（本人目視）").font(.headline)
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(["ドライ", "湿り", "濡れ", "水たまり"], id: \.self) { label in
                                Button(label) {
                                    let choices = ["ドライ": "dry", "湿り": "damp",
                                                   "濡れ": "wet", "水たまり": "puddle"]
                                    recorder.addCondition(category: "road_surface", value: choices[label])
                                }
                                .buttonStyle(.borderedProminent)
                                .disabled(!recorder.isTracking)
                            }
                        }
                        Text("天気（本人目視）").font(.headline)
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(["晴れ", "曇り", "雨", "霧"], id: \.self) { label in
                                Button(label) {
                                    let choices = ["晴れ": "clear", "曇り": "cloudy",
                                                   "雨": "rain", "霧": "fog"]
                                    recorder.addCondition(category: "weather", value: choices[label])
                                }
                                .buttonStyle(.bordered)
                                .disabled(!recorder.isTracking)
                            }
                        }
                        Text("気温（℃）・温度計で実測した場合のみ").font(.headline)
                        TextField("例：23.5　未測定なら空欄", text: $measuredAirTemperature)
                            .keyboardType(.decimalPad)
                            .textFieldStyle(.roundedBorder)
                        Button("実測した気温を記録") {
                            if let celsius = Double(measuredAirTemperature),
                               celsius.isFinite, (-30...60).contains(celsius) {
                                recorder.addCondition(category: "air_temperature",
                                                      temperatureC: celsius)
                                conditionFeedback = "温度計での実測値として保存を依頼しました。"
                            } else {
                                conditionFeedback = "未測定なら入力不要。数値は実測値だけにしてください。"
                            }
                        }
                        .disabled(!recorder.isTracking)
                        if !conditionFeedback.isEmpty {
                            Text(conditionFeedback).font(.footnote)
                        }
                    }
                    Text("捕獲・目撃の記録").font(.headline)
                    Picker("記録種別", selection: $category) {
                        ForEach(["捕獲", "目撃", "轢死", "その他"], id: \.self) { Text($0) }
                    }.pickerStyle(.segmented)
                    TextField("生き物の種類", text: $species)
                        .textFieldStyle(.roundedBorder)
                    TextField("匹数（整数）", text: $quantity)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                    Picker("記録者（本人捕獲の判定用）", selection: $observationOwner) {
                        Text("未確認").tag("unknown")
                        Text("本人").tag("self")
                        Text("他者").tag("other")
                    }.pickerStyle(.menu)
                    TextField("備考（サイズ・性別・路面など）", text: $observationNote)
                        .textFieldStyle(.roundedBorder)
                    Button("端末内に観察を保存") {
                        let types = ["捕獲": "capture", "目撃": "sighting",
                                     "轢死": "roadkill", "その他": "other"]
                        recorder.addObservation(
                            type: types[category] ?? "other",
                            species: species,
                            number: Int(quantity) ?? -1,
                            owner: observationOwner == "unknown" ? nil : observationOwner,
                            note: observationNote
                        )
                    }.disabled(!recorder.isTracking)
                    Divider()
                    Text("暗号化したGPS原本の自動同期").font(.headline)
                    Text("初回だけiPhoneの「ファイル」からGoogle Driveの非公開HabuAI_Encrypted_Inboxフォルダを選択。探索終了時と次回起動時に、GPS原本を端末内で暗号化して保存先に書き込みます。パスフレーズ入力は不要。")
                        .font(.footnote)
                    Text(recorder.inboxStatus)
                        .font(.footnote)
                        .accessibilityIdentifier("privateInboxStatus")
                    HStack {
                        Button(recorder.isInboxConfigured ? "同期フォルダを変更" : "初回のみ：同期フォルダを選ぶ") {
                            showInboxFolderPicker = true
                        }
                        .disabled(recorder.isTracking)
                        Button("未送信原本を再試行") {
                            recorder.retryPendingInbox()
                        }
                        .disabled(!recorder.isInboxConfigured)
                    }
                    .buttonStyle(.bordered)
                    Text("この表示は端末からフォルダへの書込み確認です。クラウド・ChatGPT Library到着は、別の読戻し検証を通過するまで成功扱いにしません。")
                        .font(.footnote).foregroundStyle(.secondary)
                    Divider()
                    Text("GPS・捕獲地点の暗号化バックアップ").font(.headline)
                    Text("AES-256-GCMで暗号化し復元検証してから共有します。復元用パスフレーズは保存されません。バックアップと別の安全な場所に控えてください。")
                        .font(.footnote)
                    SecureField("復元用パスフレーズ（12文字以上）", text: $backupPassphrase)
                        .textContentType(.newPassword)
                        .textFieldStyle(.roundedBorder)
                    SecureField("パスフレーズ再入力", text: $backupConfirmation)
                        .textContentType(.newPassword)
                        .textFieldStyle(.roundedBorder)
                    Button("🔐 原本を暗号化してバックアップ") {
                        let password = backupPassphrase
                        if password.unicodeScalars.count < 12 ||
                           password != backupConfirmation {
                            backupMessage = "12文字以上のパスフレーズを一致させてください。"
                        } else {
                            sealedBackup = recorder.encryptedBackup(
                                sessionId: selectedSessionId, passphrase: password
                            )
                            backupMessage = sealedBackup == nil
                                ? "暗号化に失敗。探索原本は変更していません。"
                                : "暗号化と復元検証に成功。暗号化ファイルのみ共有できます。"
                        }
                        backupPassphrase = ""
                        backupConfirmation = ""
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedSessionId.isEmpty || recorder.isTracking)
                    if let sealedBackup {
                        ShareLink(item: sealedBackup) {
                            Label("暗号化ファイル（.habuenc）を保存・共有",
                                  systemImage: "lock.shield")
                        }
                    }
                    Button("暗号化バックアップを選択して復元") {
                        showEncryptedBackupPicker = true
                    }
                    .disabled(recorder.isTracking || recorder.hasUnfinishedSession)
                    if !backupMessage.isEmpty {
                        Text(backupMessage).font(.footnote)
                    }
                    Divider()
                    Text("GPX・原記録の出力").font(.headline)
                    Text("以下は非暗号化の旧方式です。GPSや捕獲地点がそのまま見えるので、私有保存先以外には共有しないでください。通常は上の暗号化バックアップを使用。")
                        .font(.footnote).foregroundStyle(.secondary)
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
                                exportedFiles = []
                                exported = recorder.export("gpx", sessionId: selectedSessionId)
                            }
                            Button("ハブログTXT") {
                                exportedFiles = []
                                exported = recorder.export("txt", sessionId: selectedSessionId)
                            }
                        }.buttonStyle(.bordered)
                        HStack {
                            Button("元ログJSONL") {
                                exportedFiles = []
                                exported = recorder.export("jsonl", sessionId: selectedSessionId)
                            }
                            Button("原本そのまま") {
                                exportedFiles = []
                                exported = recorder.export("raw", sessionId: selectedSessionId)
                            }
                        }.buttonStyle(.bordered)
                        Button("ハブログとGPXをまとめて作成") {
                            exported = nil
                            exportedFiles = []
                            if let text = recorder.export("txt", sessionId: selectedSessionId),
                               let track = recorder.export("gpx", sessionId: selectedSessionId) {
                                exportedFiles = [text, track]
                            }
                        }.buttonStyle(.bordered)
                        Text("GPSは実測点だけから生成。本人の捕獲数は確定集計に自動加算しません。")
                            .font(.footnote)
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
                    if !exportedFiles.isEmpty {
                        ShareLink(items: exportedFiles) { Label("ハブログ・GPXを保存・共有", systemImage: "square.and.arrow.up") }
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
            .onChange(of: recorder.isTracking) { tracking in
                guard tracking else { return }
                // A retained older selection must not hide the search just
                // started or resumed by the owner.
                if let id = recorder.activeSessionId {
                    selectedSessionId = id
                }
                recordEvidenceText = ""
                exported = nil
                exportedFiles = []
            }
            .onChange(of: selectedSessionId) { _ in
                // A share link belongs to the selected original only.
                recordEvidenceText = ""
                exported = nil
                exportedFiles = []
                sealedBackup = nil
            }
            .fileImporter(isPresented: $showInboxFolderPicker,
                          allowedContentTypes: [.folder],
                          allowsMultipleSelection: false) { result in
                switch result {
                case .success(let folders):
                    if let folder = folders.first {
                        recorder.configureInboxFolder(folder)
                    }
                case .failure:
                    // No stored source is altered when permission is denied.
                    backupMessage = "保存先選択を中止しました。端末の原本は保持されています。"
                }
            }
            .fileImporter(isPresented: $showEncryptedBackupPicker,
                          allowedContentTypes: [.item],
                          allowsMultipleSelection: false) { result in
                let passphrase = backupPassphrase
                backupPassphrase = ""
                backupConfirmation = ""
                switch result {
                case .success(let urls):
                    if let url = urls.first, passphrase.unicodeScalars.count >= 12 {
                        let restored = recorder.restoreEncryptedBackup(
                            from: url, passphrase: passphrase
                        )
                        backupMessage = restored
                            ? "復号検証と原本復元に成功。重複は作成しません。"
                            : "復号・検証・復元に失敗。原本を上書きしません。"
                    } else {
                        backupMessage = "復元用パスフレーズを入力してからファイルを選択してください。"
                    }
                case .failure:
                    backupMessage = "ファイルを選択できませんでした。"
                }
            }
        }
    }
}
