"""Exercise patched error paths from the locked sources with real Qt types."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = os.environ.get('WARNING_SOURCE_DIR')
PACKAGE = os.environ.get('WARNING_SOURCE_PACKAGE')


def function(relative, signature):
    text = (Path(ROOT) / relative).read_text(encoding='utf-8')
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2]


def execute(source):
    flags = shlex.split(subprocess.check_output(
        ['pkg-config', '--cflags', '--libs', 'Qt5Core', 'Qt5Gui'], text=True))
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'fallbacks.cpp'
        binary = Path(temporary) / 'fallbacks'
        path.write_text(source, encoding='utf-8')
        subprocess.run(['g++', '-std=c++17', '-fPIC', '-Werror=return-type',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(path), '-o', str(binary), *flags], check=True)
        subprocess.run([str(binary)], check=True)


@unittest.skipUnless(ROOT and shutil.which('g++'), 'requires patched source and Linux Qt compiler')
class BuildWarningRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(PACKAGE == 'kylin-os-installer', 'installer source only')
    def test_installer_model_children_and_empty_device_path(self):
        device = function('src/plugins/KPartition/partman/device.cpp',
                          'QString Device::getDevicePath()')
        combo = function('src/plugins/PluginService/ui_unit/comboxlistmodel.cpp',
                         'int ComboxListModel::rowCount(')
        zones = function('src/plugins/KTimeZone/timezonemodel.cpp',
                         'int TimeZoneModel::rowCount(')
        execute('''
#include <QString>
#include <QStringList>
#include <QStandardItemModel>
#include <cassert>
struct Device { QString m_path; QString getDevicePath(); };
struct ComboxListModel { QStringList m_languageList; int rowCount(const QModelIndex &) const; };
struct TimeZoneModel { QStringList m_TZLists; int rowCount(const QModelIndex &) const; };
''' + device + '\n' + combo + '\n' + zones + '''
int main() {
    Device device;
    assert(device.getDevicePath().isEmpty());
    device.m_path = "/dev/example";
    assert(device.getDevicePath() == "/dev/example");
    QStandardItemModel parentModel(1, 1);
    const QModelIndex child = parentModel.index(0, 0);
    assert(child.isValid());
    ComboxListModel languages{{"en", "vi"}};
    TimeZoneModel zones{{"UTC"}};
    assert(languages.rowCount(QModelIndex()) == 2);
    assert(zones.rowCount(QModelIndex()) == 1);
    assert(languages.rowCount(child) == 0);
    assert(zones.rowCount(child) == 0);
}
''')

    @unittest.skipUnless(PACKAGE == 'ukui-greeter', 'greeter source only')
    def test_greeter_date_sdk_failure_and_allocation_lifetime(self):
        date = function('ukui-greeter/greeter/greeterwindow.cpp',
                        'QString GreeterWindow::getLongFormatDate(int type)')
        execute('''
#include <QString>
#include <cassert>
enum { DATE, TIME };
struct kdk_logn_dateinfo { const char *date, *week, *time; };
static kdk_logn_dateinfo info{"2026-11-08", "Sunday", "12:00"};
static bool failSdk = false;
static int frees = 0;
static kdk_logn_dateinfo *kdk_system_login_lock_dateinfo(char *) {
    return failSdk ? nullptr : &info;
}
static void kdk_free_logn_dateinfo(kdk_logn_dateinfo *p) {
    assert(p == &info);
    ++frees;
}
struct GreeterWindow {
    QString currentUser{"test"};
    QString getLongFormatDate(int);
};
''' + date + '''
int main() {
    GreeterWindow window;
    failSdk = true;
    assert(window.getLongFormatDate(DATE).isEmpty());
    assert(frees == 0);
    failSdk = false;
    assert(window.getLongFormatDate(DATE) == "2026-11-08 Sunday");
    assert(frees == 1);
    assert(window.getLongFormatDate(TIME) == "12:00");
    assert(frees == 2);
    assert(window.getLongFormatDate(99).isEmpty());
    assert(frees == 3);
}
''')
