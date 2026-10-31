package org.habuai.field

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.*
import java.io.IOException

/** Start service while visible; screen lock and Home do not stop foreground service. */
class MainActivity : Activity() {
    private val store by lazy { TrackingStore(this) }
    private lateinit var status: TextView
    private lateinit var count: EditText
    private lateinit var species: EditText
    private lateinit var kind: Spinner
    private var exportKind: String = "gpx"
    private var exportSessionId: String? = null
    private val permissionRequest = 401
    private val exportRequest = 402
    private val notificationPermissionRequest = 403

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        exportKind = savedInstanceState?.getString("pending_export_kind") ?: "gpx"
        exportSessionId = savedInstanceState?.getString("pending_export_id")
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }
        val root = ScrollView(this)
        root.addView(layout)
        setContentView(root)

        layout.addView(TextView(this).apply {
            text = "HABU FIELD GPS / Android"
            textSize = 23f
        })
        layout.addView(TextView(this).apply {
            text = "画面ロック中も通知を表示してGPSを記録。圏外でも端末に保存。" +
                " 強制停止・GPS無効・OS制限中は測位を保証できません。"
        })
        status = TextView(this).apply { textSize = 17f }
        layout.addView(status)

        layout.addView(button("探索開始・画面ロック中もGPS記録") { startTracking() })
        layout.addView(button("探索終了・GPS停止") { stopTracking() })
        layout.addView(button("未終了の保存記録を確認") { showOrphans() })
        layout.addView(button("過去の探索記録を選んで書き出す") { showAllSessions() })

        layout.addView(TextView(this).apply { text = "生き物の種類（例：ハブ、アカマタ）" })
        species = EditText(this).apply { setText("ハブ"); hint = "生き物" }
        layout.addView(species)
        kind = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                listOf("捕獲", "目撃", "轢死", "その他"))
        }
        layout.addView(kind)
        count = EditText(this).apply {
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setText("1")
            hint = "匹数"
        }
        layout.addView(count)
        layout.addView(button("観察を端末に保存（確定集計には未反映）") {
            val kindValue = listOf("capture", "sighting", "roadkill", "other")[kind.selectedItemPosition]
            try {
                store.observation(kindValue, species.text.toString().trim(),
                    count.text.toString().toIntOrNull() ?: -1)
                refresh("観察を端末内に保存")
            } catch (e: Exception) { refresh("保存できません: " + e.message) }
        })
        layout.addView(button("実測GPXをファイルに保存") { export("gpx") })
        layout.addView(button("元イベント記録をJSONLで保存") { export("ndjson") })
        layout.addView(TextView(this).apply {
            text = "測位は常に実測だけ。5分以上の欠測・GPS停止はGPXを別セグメントに分離。" +
                " インターネット通信権限なし。クラウドへ自動アップロードしません。"
        })
        refresh()
    }
    private fun button(label: String, onClick: () -> Unit): View =
        Button(this).apply { text = label; setOnClickListener { onClick() } }

    private fun showOrphans() {
        val ids = store.orphanedStarts()
        if (ids.isEmpty()) return refresh("未終了の保存記録はありません")
        val options = ids.map { id ->
            val count = try { store.read(id).size.toString() } catch (_: Exception) { "読取不可・原本保持" }
            id + " / 記録 " + count + "件"
        }
        AlertDialog.Builder(this)
            .setTitle("未終了の探索記録（GPSは自動再開しません）")
            .setItems(options.toTypedArray()) { _, index ->
                // Explicit choice only; never send the raw file to a remote server.
                export("raw", ids[index])
            }
            .setPositiveButton("閉じる", null)
            .show()
    }
    private fun showAllSessions() {
        val ids = store.allSessionIds()
        if (ids.isEmpty()) return refresh("保存された探索記録はありません")
        val labels = ids.mapIndexed { index, id ->
            val suffix = if (id == store.activeId()) "（未終了）" else ""
            "${index + 1}: ${id.take(8)}$suffix"
        }
        AlertDialog.Builder(this)
            .setTitle("保存済み探索を選択（端末内のみ）")
            .setItems(labels.toTypedArray()) { _, index ->
                val id = ids[index]
                AlertDialog.Builder(this)
                    .setTitle("記録 ${id.take(8)} の書き出し")
                    .setItems(arrayOf("実測GPX", "解析用NDJSON", "原本をそのまま保存")) { _, typeIndex ->
                        val type = when (typeIndex) {
                            0 -> "gpx"
                            1 -> "ndjson"
                            else -> "raw"
                        }
                        export(type, id)
                    }
                    .setNegativeButton("キャンセル", null)
                    .show()
            }
            .setNegativeButton("閉じる", null)
            .show()
    }

    private fun startTracking() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            // An approximate-only grant cannot provide offline GNSS fixes.
            // Never silently replace an actual GPS route with coarse network estimates.
            if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                refresh("正確な位置情報が必要です。端末の設定でこのアプリの「正確な位置情報」を許可してください。")
            } else {
                requestPermissions(arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION), permissionRequest)
            }
            return
        }
        // Android 13+ may hide the persistent tracking notification without consent.
        // Require it before starting: location recording must stay visible to the owner.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), notificationPermissionRequest)
            return
        }
        try {
            store.create()
            startForegroundService(Intent(this, LocationTrackingService::class.java)
                .setAction(LocationTrackingService.START))
            refresh("探索開始。通知にGPS記録中と表示されます。")
        } catch (e: Exception) { refresh("開始できません: " + e.message) }
    }
    private fun stopTracking() {
        if (store.activeId() != null) {
            startService(Intent(this, LocationTrackingService::class.java)
                .setAction(LocationTrackingService.STOP))
            refresh("探索終了を要求しました")
        } else refresh("記録中の探索はありません")
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, results)
        if (requestCode == permissionRequest) {
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) startTracking()
            else refresh("GPS記録には「正確な位置情報」の許可が必要です。設定で許可してください。")
        } else if (requestCode == notificationPermissionRequest) {
            if (results.firstOrNull() == PackageManager.PERMISSION_GRANTED) startTracking()
            else refresh("通知が許可されていません。記録中の通知を表示できないためGPSは開始しません。設定から通知を許可してください。")
        }
    }
    private fun refresh(extra: String? = null) {
        val running = store.activeId()
        val latest = store.latestId()
        status.text = (if (extra != null) extra + "\n" else "") +
            (if (running != null)
                "未終了の探索: " + running + "\nGPS稼働は通知で確認。停止中なら「探索開始」を押して再開してください。"
                else "GPS停止 / 最後の記録: " + (latest ?: "なし"))
    }
    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString("pending_export_kind", exportKind)
        outState.putString("pending_export_id", exportSessionId)
    }
    private fun export(type: String, selectedId: String? = null) {
        val id = selectedId ?: store.latestId() ?: return refresh("記録がありません")
        exportKind = type
        // Freeze the requested session and format before opening the system file picker.
        // A screen rotation must never export a different session or wrong file type.
        exportSessionId = id
        val i = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            this.type = if (type == "gpx") "application/gpx+xml" else "application/x-ndjson"
            val extension = if (type == "raw") "ndjson" else type
            putExtra(Intent.EXTRA_TITLE, "habu-" + id + "." + extension)
        }
        startActivityForResult(i, exportRequest)
    }
    @Deprecated("Uses Storage Access Framework, no broad storage permission")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != exportRequest) return
        if (resultCode != RESULT_OK) {
            exportSessionId = null
            return
        }
        val uri: Uri = data?.data ?: run {
            exportSessionId = null
            return refresh("保存場所を選べませんでした")
        }
        try {
            val id = exportSessionId ?: error("書き出す記録が特定できません。もう一度選び直してください")
            val bytes = if (exportKind == "raw") {
                // Byte-exact backup of unreadable/truncated sources; no parsing,
                // alteration or invented GPS points.
                store.rawBytes(id)
            } else {
                val entries = store.read(id)
                val content = if (exportKind == "gpx") TrackExport.toGpx(entries)
                  else TrackExport.toLog(entries)
                content.toByteArray(Charsets.UTF_8)
            }
            contentResolver.openOutputStream(uri, "w").use { out ->
                if (out == null) throw IOException("出力先が開けません")
                out.write(bytes)
                out.flush()
            }
            refresh(exportKind + " を保存しました。原本の共有先に注意してください。")
        } catch (e: Exception) { refresh("保存に失敗: " + e.message) }
        finally { exportSessionId = null }
    }
    override fun onResume() {
        super.onResume()
        if (::status.isInitialized) refresh()
    }
}
