package org.habuai.field
fun main() {
  val rows = listOf("a" to listOf("start"), "b" to listOf("start", "stop"), "c" to listOf("start", "fix"))
  check(SessionRecovery.pending(null, rows) == listOf("a", "c"))
  check(SessionRecovery.pending("a", rows) == listOf("c"))
  println("SESSION_RECOVERY_TEST_PASS")
}
