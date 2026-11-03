package org.habuai.field

/** Only accept observations measured at or after the owner's explicit start. */
object GpsFixPolicy {
    fun isFresh(fixElapsedNanos: Long, startedElapsedNanos: Long): Boolean =
        startedElapsedNanos != Long.MAX_VALUE && fixElapsedNanos >= startedElapsedNanos
}
