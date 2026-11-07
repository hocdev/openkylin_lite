/* SPDX-License-Identifier: LGPL-3.0-or-later
 * ABI compatibility for applications linked to libkysdk-datacollect.so.1.
 * No identity reads, event storage, D-Bus, subprocesses or network operations.
 */
#include "libkydatacollect.h"
#include <stdlib.h>

KTrackData *kdk_dia_data_init(KEventSourceType source, KEventType type)
{
    KTrackData *node = calloc(1, sizeof(*node));
    if (!node) return NULL;
    node->globalProperty = calloc(1, sizeof(*node->globalProperty));
    if (!node->globalProperty) { free(node); return NULL; }
    /* Existing clients may dereference these strings. Return empty values,
     * never machine IDs, addresses, package names or registration details. */
    node->appName = calloc(1, 1);
    node->appVersion = calloc(1, 1);
    node->globalProperty->umid = calloc(1, 1);
    node->globalProperty->userId = calloc(1, 1);
    node->globalProperty->sourceIp = calloc(1, 1);
    node->globalProperty->sourceMac = calloc(1, 1);
    node->globalProperty->serviceKey = calloc(1, 1);
    node->globalProperty->registerNumber = calloc(1, 1);
    if (!node->appName || !node->appVersion || !node->globalProperty->umid ||
        !node->globalProperty->userId || !node->globalProperty->sourceIp ||
        !node->globalProperty->sourceMac || !node->globalProperty->serviceKey ||
        !node->globalProperty->registerNumber) {
        kdk_dia_data_free(node);
        return NULL;
    }
    node->eventSourceType = source;
    node->eventType = type;
    return node;
}

void kdk_dia_data_free(KTrackData *node)
{
    if (!node) return;
    free(node->eventCode);
    free(node->pageName);
    free(node->pageUrl);
    free(node->pagePath);
    free(node->appName);
    free(node->appVersion);
    free(node->searchWord);
    free(node->entrancePageFlag);
    free(node->exitPageFlag);
    if (node->globalProperty) {
        free(node->globalProperty->umid);
        free(node->globalProperty->userId);
        free(node->globalProperty->sourceIp);
        free(node->globalProperty->sourceMac);
        free(node->globalProperty->serviceKey);
        free(node->globalProperty->registerNumber);
        free(node->globalProperty);
    }
    /* The upstream API leaves ownership of customProperty with the caller. */
    free(node);
}

void kdk_dia_upload_program_startup(void) {}
void kdk_dia_upload_program_exit(void) {}
void kdk_dia_upload_search_content(KTrackData *n, char *e, char *p, char *c)
{ (void)n; (void)e; (void)p; (void)c; }
void kdk_dia_upload_default(KTrackData *n, char *e, char *p)
{ (void)n; (void)e; (void)p; }
void kdk_dia_append_page_info(KTrackData *n, char *u, char *p)
{ (void)n; (void)u; (void)p; }
void kdk_dia_append_page_flag(KTrackData *n, bool a, bool b)
{ (void)n; (void)a; (void)b; }
void kdk_dia_append_custom_property(KTrackData *n, KCustomProperty *p, int length)
{ (void)n; (void)p; (void)length; }
