package org.habuai.field

/** Run with kotlinc and java; no Android SDK required. */
fun main() {
    val events = mutableListOf<String>()
    SessionStartCoordinator.begin({ events.add("start") }, { events.add("active"); true })
    check(events == listOf("start", "active"))

    events.clear()
    try {
        SessionStartCoordinator.begin({ events.add("start") }, { events.add("failed"); false })
        error("expected failure")
    } catch (e: IllegalStateException) {
        check(e.message == "Could not persist active session")
    }
    check(events == listOf("start", "failed"))

    events.clear()
    try {
        SessionStartCoordinator.begin(
            { events.add("write-failed"); throw IllegalStateException("disk") },
            { events.add("active"); true }
        )
    } catch (e: IllegalStateException) {
        check(e.message == "disk")
    }
    check(events == listOf("write-failed"))
    println("SESSION_START_FAULT_TEST_PASS")
}
