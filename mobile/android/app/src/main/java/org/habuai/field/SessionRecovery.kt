package org.habuai.field

internal object SessionRecovery {
    fun pending(active: String?, entries: List<Pair<String,List<String>>>): List<String> =
        entries.filter { (id, kinds) -> id != active && kinds.firstOrNull() == "start" && !kinds.contains("stop") }
            .map { it.first }.sorted()
}
