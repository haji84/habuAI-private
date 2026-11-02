#!/usr/bin/env python3
"""Classify a local Xcode build failure without disclosing signing secrets.

The caller supplies a private build.log path. This tool prints ONLY a fixed
category name; it never prints any excerpts, paths, developer IDs, emails,
profile IDs, device IDs, IP addresses, certificate hashes, or raw Xcode logs.
It does not modify Xcode/Keychain/provisioning assets.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def classify(log: str) -> str:
    text = log.lower()
    patterns = (
        # Separate "Xcode has no signed-in accounts" from "the selected
        # signing Team ID is not accessible by any configured account".
        # A certificate's Team ID alone is not evidence of Xcode account access.
        ("TEAM_ACCOUNT_MISMATCH", (
            r"no account for team",
        )),
        ("XCODE_NO_ACCOUNTS", (
            r"there are no accounts registered",
            r"no accounts",
            r"add an account",
        )),
        ("ACCOUNT_AUTH_REQUIRED", (
            r"not signed in",
            r"account.*is not available",
        )),
        ("AGREEMENT_REQUIRED", (
            r"license agreement.*(updated|accept|agree)",
            r"(accept|agree).*(license|agreement)",
            r"program license agreement",
        )),
        ("BUNDLE_ID_UNAVAILABLE", (
            r"failed to register bundle identifier",
            r"app id .*not available",
            r"identifier .*not available",
            r"identifier .*already (in use|registered|taken)",
            r"bundle identifier.*(unavailable|not available|already)",
            r"cannot be registered to your development team",
        )),
        ("CERTIFICATE_NOT_USABLE", (
            r"no signing certificate",
            r"signing certificate.*(not found|missing|expired|invalid)",
            r"code signing identity.*(not found|missing|invalid)",
            r"private key.*(missing|not found)",
            r"(no|missing) private key",
            r"certificate.*(revoked|expired)",
        )),
        ("DEVICE_NOT_REGISTERED", (
            r"device.*not registered",
            r"no devices.*(registered|available)",
            r"provisioning profile.*(doesn't|does not) include",
            r"register.*device.*developer account",
        )),
        ("CAPABILITY_NOT_ALLOWED", (
            r"personal team.*(does not support|unsupported)",
            r"capability.*(not available|not supported)",
            r"entitlement.*(not supported|not permitted)",
        )),
        ("PROVISIONING_PROFILE_MISSING", (
            r"no profiles for",
            r"no provisioning profiles",
            r"provisioning profile.*(not found|missing|doesn't exist|could not be found)",
            r"requires a provisioning profile",
        )),
        ("DEVELOPER_SERVICE_UNAVAILABLE", (
            r"developer portal.*(unavailable|offline|could not)",
            r"(network|connection).*timed out",
            r"could not connect.*(apple|developer)",
            r"service.*temporarily unavailable",
            r"could not communicate with apple",
        )),
        ("COMPILATION_ERROR", (
            r"(^|\n).*\.swift:\d+:\d+: error:",
            r"error:.*(cannot find|has no member|not convertible|ambiguous use)",
            r"swiftcompile.*failed",
        )),
    )
    for code, checks in patterns:
        if any(re.search(pattern, text) for pattern in checks):
            return code
    # SIGNING_FAILED was an overclaim; without a matching error the cause is
    # unknown, even if a generic log mentions signing during normal build.
    return "BUILD_FAILURE_UNCLASSIFIED"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("BUILD_FAILURE_UNCLASSIFIED")
        return 0
    try:
        log = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        print("BUILD_FAILURE_UNCLASSIFIED")
        return 0
    print(classify(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
