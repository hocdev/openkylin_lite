The headers retain the upstream LGPL-3.0-or-later notices and public C ABI.

`libkydatacollect.h` comes from `libkysdk-diagnosetest 3.0.1.0`, with the Debian
patches in `3.0.1.0-0k0.1update1` applied. The source archives and their SHA256
pins are in `scripts/build_privacy_sdk.sh`.

`libkydiagnostics.h` comes from `libkysdk-base 3.0.1.0`:
https://archive.build.openkylin.top/openkylin/pool/main/libk/libkysdk-base/libkysdk-base_3.0.1.0.orig.tar.xz

Both replacement C implementations retain only ABI compatibility. They do not
read identity, serialise or store events, make IPC/network calls, or launch
processes. The current API allocates empty structures because desktop clients
dereference them; returning NULL unconditionally would break those clients.
