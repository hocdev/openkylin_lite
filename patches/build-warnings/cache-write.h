#ifndef OPENKYLIN_LITE_CACHE_WRITE_H
#define OPENKYLIN_LITE_CACHE_WRITE_H

#include <cerrno>
#include <cstddef>
#include <unistd.h>

namespace UkuiLite {
inline bool writeAll(int fd, const void *data, std::size_t size)
{
    const char *bytes = static_cast<const char *>(data);
    while (size != 0) {
        const ssize_t count = ::write(fd, bytes, size);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            return false;
        }
        bytes += count;
        size -= static_cast<std::size_t>(count);
    }
    return true;
}
}

#endif
