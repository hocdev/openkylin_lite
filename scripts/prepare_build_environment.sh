#!/usr/bin/env bash
# Build containers have no service manager. Make that policy explicit to maintainer scripts.
set -Eeuo pipefail
if [[ ! -e /usr/sbin/policy-rc.d && ! -L /usr/sbin/policy-rc.d ]]; then
  printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
  chmod 0755 /usr/sbin/policy-rc.d
fi
