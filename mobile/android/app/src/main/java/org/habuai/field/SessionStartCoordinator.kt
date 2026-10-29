package org.habuai.field

/** Testable ordering for a durable start record and its active marker. */
internal object SessionStartCoordinator {
    fun begin(writeStart: () -> Unit, persistActive: () -> Boolean) {
        writeStart()
        if (!persistActive()) throw IllegalStateException("Could not persist active session")
    }
}
