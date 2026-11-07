/* SPDX-License-Identifier: LGPL-3.0-or-later
 * Disable the legacy telemetry ABI without replacing the rest of kysdk-base.
 */
#include "libkydiagnostics.h"
int kdk_buried_point(char *app, char *type, KBuriedPoint *data, int length)
{
    (void)app; (void)type; (void)data; (void)length;
    return 0;
}
