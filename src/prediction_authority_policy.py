"""Shared descriptive policy; these constants never grant execution authority.

Read-only diagnostics may import this module without loading registry locks,
model fitting, or inference. The registry still enforces its own live context.
"""

AUTHORITY_BLOCKER = 'IMPLEMENTATION_BLOCKED: Task8 trusted reproduction, exact-head CI and reviewed durable activation authority unavailable'
SCOPE = 'SANDBOX_MECHANICS'
