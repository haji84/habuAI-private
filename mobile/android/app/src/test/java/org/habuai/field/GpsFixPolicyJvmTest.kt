package org.habuai.field

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Synthetic monotonic times only: no location or owner data. */
class GpsFixPolicyJvmTest {
    @Test fun rejectsCachedFixMeasuredThreeSecondsBeforeStart() {
        val startedAt = 1_000_000_000_000L
        val cachedFix = startedAt - 3_000_000_000L
        assertFalse(GpsFixPolicy.isFresh(cachedFix, startedAt))
        assertFalse(GpsFixPolicy.isFresh(startedAt - 1L, startedAt))
    }

    @Test fun acceptsCurrentFixAndRejectsUninitializedStart() {
        val startedAt = 1_000_000_000_000L
        assertTrue(GpsFixPolicy.isFresh(startedAt, startedAt))
        assertTrue(GpsFixPolicy.isFresh(startedAt + 1L, startedAt))
        assertFalse(GpsFixPolicy.isFresh(startedAt, Long.MAX_VALUE))
    }
}
