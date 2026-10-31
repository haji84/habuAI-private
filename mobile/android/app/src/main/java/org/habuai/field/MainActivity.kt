package org.habuai.field

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
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
    private val permissionRequest = 401
    private val exportRequest = 402

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
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
        val details = ids.map { id ->
            val count = try { store.read(id).size.toString() } catch (_: Exception) { "読取不可" }
            id + " / 記録 " + count + "件"
        }.joinToString("\n")
        AlertDialog.Builder(this)
            .setTitle("未終了の探索記録")
            .setMessage(details + "\nGPSは自動再開しません。")
            .setPositiveButton("閉じる", null)
            .show()
    }
    private fun startTracking() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION), permissionRequest)
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
            if (results.any { it == PackageManager.PERMISSION_GRANTED }) startTracking()
            else refresh("位置情報の権限がありません。")
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
    private fun export(type: String) {
        val id = store.latestId() ?: return refresh("記録がありません")
        exportKind = type
        val i = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            this.type = if (type == "gpx") "application/gpx+xml" else "application/x-ndjson"
            putExtra(Intent.EXTRA_TITLE, "habu-" + id + "." + type)
        }
        startActivityForResult(i, exportRequest)
    }
    @Deprecated("Uses Storage Access Framework, no broad storage permission")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != exportRequest || resultCode != RESULT_OK) return
        val uri: Uri = data?.data ?: return refresh("保存場所を選べませんでした")
        try {
            val id = store.latestId() ?: error("記録がありません")
            val entries = store.read(id)
            val content = if (exportKind == "gpx") TrackExport.toGpx(entries)
              else TrackExport.toLog(entries)
            contentResolver.openOutputStream(uri, "w").use { out ->
                if (out == null) throw IOException("出力先が開けません")
                out.write(content.toByteArray(Charsets.UTF_8))
                out.flush()
            }
            refresh(exportKind + " を保存しました。原本の共有先に注意してください。")
        } catch (e: Exception) { refresh("保存に失敗: " + e.message) }
    }
    override fun onResume() {
        super.onResume()
        if (::status.isInitialized) refresh()
    }
}
