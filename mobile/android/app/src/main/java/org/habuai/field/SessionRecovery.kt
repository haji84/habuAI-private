package org.habuai.field

internal object SessionRecovery {
    fun hasCompleted(kinds: List<String>): Boolean = kinds.contains("stop")

    fun canResume(kinds: List<String>): Boolean =
        kinds.firstOrNull() == "start" && !hasCompleted(kinds)

    fun pending(active: String?, entries: List<Pair<String,List<String>>>): List<String> =
        entries.filter { (id, kinds) -> id != active && canResume(kinds) }
            .map { it.first }.sorted()
}
