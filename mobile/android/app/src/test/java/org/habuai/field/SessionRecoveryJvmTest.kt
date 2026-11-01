package org.habuai.field

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pure JVM fault-contract tests. No user GPS or device permissions are read.
 * This checks the decisions that TrackingStore applies after a crash.
 */
class SessionRecoveryJvmTest {
    @Test fun completedStopMakesSessionNonResumable() {
        val stored = listOf("start", "fix", "event", "stop")
        assertTrue(SessionRecovery.hasCompleted(stored))
        assertFalse(SessionRecovery.canResume(stored))
    }

    @Test fun explicitRestartRequiresUnclosedStart() {
        assertTrue(SessionRecovery.canResume(listOf("start", "fix", "gap")))
        assertFalse(SessionRecovery.canResume(listOf("fix", "gap")))
        assertFalse(SessionRecovery.canResume(emptyList()))
        assertFalse(SessionRecovery.canResume(listOf("start", "stop", "gap")))
    }

    @Test fun orphanRecoveryDoesNotIncludeCompletedOrActiveSession() {
        val entries = listOf(
            "unfinished" to listOf("start", "fix"),
            "completed" to listOf("start", "stop"),
            "unreadable" to listOf("start", "unreadable-original"),
            "active" to listOf("start", "fix"),
            "bad" to listOf("fix")
        )
        assertEquals(
            listOf("unfinished", "unreadable"),
            SessionRecovery.pending("active", entries)
        )
    }
}
