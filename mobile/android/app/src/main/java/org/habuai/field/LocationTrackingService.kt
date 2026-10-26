package org.habuai.field

import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.*
import android.os.*
import androidx.annotation.Keep

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
    private var id: String? = null

    override fun onCreate() {
        super.onCreate()
        manager = getSystemService(LOCATION_SERVICE) as LocationManager
        store = TrackingStore(this)
        val channel = NotificationChannel(CHANNEL, "探索中のGPS測位", NotificationManager.IMPORTANCE_LOW)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == STOP) {
            end()
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
            val minTime = 5_000L
            val minDistance = 5f
            var any = false
            for (provider in listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)) {
                if (manager.isProviderEnabled(provider)) {
                    manager.requestLocationUpdates(provider, minTime, minDistance, this, Looper.getMainLooper())
                    any = true
                }
            }
            if (!any) store.gap(id!!, "no-location-provider")
        } catch (e: SecurityException) {
            store.gap(id!!, "location-permission-revoked")
            stopSelf()
            return START_NOT_STICKY
        } catch (e: RuntimeException) {
            store.gap(id!!, "foreground-service-start-error")
            stopSelf()
            return START_NOT_STICKY
        }
        // Android may restart after system reclaim; user force-stop is not bypassed.
        return START_STICKY
    }
    override fun onLocationChanged(location: Location) { id?.let { store.fix(it, location) } }
    override fun onProviderDisabled(provider: String) { id?.let { store.gap(it, "$provider-disabled") } }
    private fun end() {
        manager.removeUpdates(this)
        store.stop()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() {
        manager.removeUpdates(this)
        id?.let { if (store.activeId() == it) store.gap(it, "service-stopped-unexpectedly") }
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
