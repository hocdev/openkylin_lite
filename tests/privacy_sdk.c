#include "libkydatacollect.h"
#include "libkydiagnostics.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#ifdef __linux__
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#endif

/* Test the SDK after forbidding filesystem/network/process creation syscalls. */
#ifdef __linux__
#define DENY(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_##n, 0, 1), \
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS)
#endif
int main(void)
{
#ifdef __linux__
    struct sock_filter filter[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        DENY(open), DENY(openat), DENY(socket), DENY(connect), DENY(sendto),
        DENY(sendmsg), DENY(execve), DENY(clone), DENY(fork), DENY(vfork),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program = {sizeof(filter) / sizeof(filter[0]), filter};
    assert(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0);
    assert(prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) == 0);
#endif
    for (int i = 0; i < 100; ++i) {
        KTrackData *node = kdk_dia_data_init(KEVENTSOURCE_DESKTOP, KEVENT_CUSTOM);
        assert(node && node->globalProperty);
        assert(node->appName && !node->appName[0] && node->appVersion && !node->appVersion[0]);
        assert(!node->timeStamp[0]);
        assert(node->globalProperty->umid && !node->globalProperty->umid[0]);
        assert(node->globalProperty->sourceMac && !node->globalProperty->sourceMac[0]);
        assert(node->globalProperty->sourceIp && !node->globalProperty->sourceIp[0]);
        assert(node->globalProperty->registerNumber && !node->globalProperty->registerNumber[0]);
        kdk_dia_upload_default(node, "event", "page");
        kdk_dia_upload_search_content(node, "event", "page", "private query");
        kdk_dia_append_page_info(node, "private URL", "private path");
        kdk_dia_append_page_flag(node, true, true);
        KCustomProperty property = {"key", "private value"};
        kdk_dia_append_custom_property(node, &property, 1);
        assert(!node->eventCode && !node->pageUrl && !node->searchWord);
        assert(!node->customProperty && node->customPropertyLength == 0);
        kdk_dia_data_free(node);
    }
    kdk_dia_upload_program_startup();
    kdk_dia_upload_program_exit();
    KBuriedPoint legacy = {"key", "private value"};
    assert(kdk_buried_point("app", "event", &legacy, 1) == 0);
    kdk_dia_data_free(NULL);
    return 0;
}
