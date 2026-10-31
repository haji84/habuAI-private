package org.habuai.field

import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.*
import android.os.*

/** Must start from a visible Activity after runtime permission is granted. */
class LocationTrackingService : Service(), LocationListener {
    companion object {
        const val START = "org.habuai.field.START"
        const val STOP = "org.habuai.field.STOP"
        private const val CHANNEL = "tracking"
        private const val NOTIFY_ID = 73
    }
    private lateinit var manager: LocationManager
    private lateinit var store: TrackingStore
    // GPS callbacks flush the append-only log. Never block the main/UI thread
    // with storage fsync when many observations arrive together.
    private lateinit var locationThread: HandlerThread
    private var id: String? = null
    @Volatile private var acceptingFixes: Boolean = false
    private var startedElapsedNanos: Long = Long.MAX_VALUE
    // A provider may return a cached pre-start fix. Accept no point older
    // than five seconds before the owner's explicit tracking start.
    private val startFixToleranceNanos = 5_000_000_000L

    override fun onCreate() {
        super.onCreate()
        manager = getSystemService(LOCATION_SERVICE) as LocationManager
        store = TrackingStore(this)
        locationThread = HandlerThread("habu-gps-log-writer").apply { start() }
        val channel = NotificationChannel(CHANNEL, "探索中のGPS測位", NotificationManager.IMPORTANCE_LOW)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == STOP) {
            end()
            return START_NOT_STICKY
        }
        // Android may deliver a null Intent after reclaiming a START_STICKY
        // service. Never resume owner GPS without an explicit Start action.
        if (intent?.action != START) {
            store.activeId()?.let { store.gap(it, "service-restart-rejected") }
            stopSelf()
            return START_NOT_STICKY
        }
        // No hidden tracking: only explicit user-started session may continue.
        id = store.activeId()
        if (id == null) { stopSelf(); return START_NOT_STICKY }
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            store.gap(id!!, "location-permission-missing")
            stopSelf()
            return START_NOT_STICKY
        }
        val open = Intent(this, MainActivity::class.java)
        val pi = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = Intent(this, LocationTrackingService::class.java).setAction(STOP)
        val stopPi = PendingIntent.getService(this, 1, stop, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = Notification.Builder(this, CHANNEL)
            .setContentTitle("ハブ探索 GPS記録中")
            .setContentText("画面ロック中も測位しています。停止するにはタップ")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentIntent(pi)
            .addAction(Notification.Action.Builder(null, "探索終了", stopPi).build())
            .setOngoing(true).build()
        try {
            if (Build.VERSION.SDK_INT >= 29)
                startForeground(NOTIFY_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
            else startForeground(NOTIFY_ID, notification)
            manager.removeUpdates(this)
            startedElapsedNanos = SystemClock.elapsedRealtimeNanos()
            acceptingFixes = true
            val minTime = 5_000L
            val minDistance = 5f
            var any = false
            val fineGranted = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
            val providers = if (fineGranted)
                listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            else listOf(LocationManager.NETWORK_PROVIDER)
            for (provider in providers) {
                if (manager.isProviderEnabled(provider)) {
                    manager.requestLocationUpdates(provider, minTime, minDistance, this, locationThread.looper)
                    any = true
                }
            }
            if (!any) {
                acceptingFixes = false
                store.gap(id!!, "no-location-provider")
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
        } catch (e: SecurityException) {
            acceptingFixes = false
            store.gap(id!!, "location-permission-revoked")
            stopSelf()
            return START_NOT_STICKY
        } catch (e: RuntimeException) {
            acceptingFixes = false
            store.gap(id!!, "foreground-service-start-error")
            stopSelf()
            return START_NOT_STICKY
        }
        // Restart only after another explicit visible user action; the owner
        // can inspect the previous session and missing points on reopening.
        return START_NOT_STICKY
    }
    override fun onLocationChanged(location: Location) {
        if (!acceptingFixes) return
        // elapsedRealtimeNanos is monotonic, unlike wall-clock timestamps,
        // so it rejects cached locations even after a device-clock change.
        if (location.elapsedRealtimeNanos < startedElapsedNanos - startFixToleranceNanos) return
        id?.let { sessionId ->
            try {
                store.fix(sessionId, location)
            } catch (_: Exception) {
                // A full/unwritable device must not keep a falsely "recording"
                // service alive. Keep the unfinished log for explicit recovery.
                try { store.gap(sessionId, "location-write-failed") } catch (_: Exception) {}
                acceptingFixes = false
                manager.removeUpdates(this)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
    }
    override fun onProviderDisabled(provider: String) {
        if (acceptingFixes) id?.let { store.gap(it, "$provider-disabled") }
    }
    private fun end() {
        acceptingFixes = false
        manager.removeUpdates(this)
        store.stop()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() {
        acceptingFixes = false
        manager.removeUpdates(this)
        id?.let {
            if (store.activeId() == it) {
                try { store.gap(it, "service-stopped-unexpectedly") } catch (_: Exception) {}
            }
        }
        if (::locationThread.isInitialized) locationThread.quitSafely()
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
