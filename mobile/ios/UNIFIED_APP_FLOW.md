# ハブAI iPhone統合アプリ：探索・記録・Google Drive保存

Status: Draft implementation on PR #92. No distribution, upload of private GPS, production model connection, or main merge is authorized by this document.

## 1つのアプリの構成

- **探索**: Existing native `ContentView` owns the single `BackgroundTrackRecorder` instance. User presses 探索開始; location fixes, 捕獲, 目撃, road conditions, and 探索終了 use the same append-only, per-session local JSONL. Observations attach a previously persisted GPS fix only when a sufficiently fresh, real fix is available. A missing fix remains missing.
- **ハブAI**: Read-only integration/status screen. A verified P0/P1 model prediction feed is **not yet connected**, so do not present a conversational estimate as a frozen official prediction or automatically promote research labels.
- **ダッシュボード**: Offline, coordinate-free, **unconfirmed** device summary from completed local JSONL sessions. Shows personally caught Habu, Habu sightings, other-fauna sightings, completed sessions and evidence holds separately. 07:00 JST night boundary. A read-only in-app WebKit sheet opens the existing owner-protected, separately reconciled historical dashboard; no native GPS data is passed to that website.

## End-to-end capture flow

`探索開始 → 実GPSを端末に追記 → 捕獲／目撃を個別に記録 → 探索終了 → 完了した元JSONLを端末で暗号化 → iOS Filesで選択済みのHabuAI_Encrypted_Inboxフォルダへ書込み・ローカル読戻し`

A session must be closed with a saved stop record to be eligible for automatic encrypted staging. The original stays on device on failure, and is retried on later start / owner action / app foreground return. The app's status **never** claims that iOS File Provider staging proves actual remote Google Drive reception. The owner must enable Google Drive in iOS Files and select the intended non-shared folder, once, with the actual phone. Nothing is uploaded to public GitHub or a static dashboard.

## After inbox arrival (not yet an automatic native feature)

Independent remote ciphertext readback, decryption under the owner-controlled private key, source SHA and duplicate verification, scientific evidence eligibility, private intake confirmation, learning, and authorized dashboard revision each require their own success evidence. Device GPS passage is never a scientific Habu-absence/Negative label. The historical confirmed total is **not** overwritten by device provisional counts.

## Release checks

- Native source contract, iOS Swift syntax, iOS simulator build, new local-summary synthetic unit tests and 3-tab UI smoke must pass on exactly the same SHA.
- Existing real iPhone lock/offline recorder evidence is retained; a changed navigation shell does not silently invalidate it, but this is not a new production-device auto-sync proof.
- Complete public-source privacy remediation, independent review and owner approval are still required before a main merge or external distribution.
