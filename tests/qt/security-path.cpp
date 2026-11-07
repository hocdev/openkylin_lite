#include "securitypathprovider.h"
#include <QCoreApplication>
#include <QDBusVirtualObject>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QProcess>
#include <QTimer>
#include <QMap>
#include <cstdio>
#include <cstdlib>

static void require(bool ok) { if (!ok) std::abort(); }
static void runFor(int ms)
{
    QEventLoop loop;
    QTimer::singleShot(ms, &loop, &QEventLoop::quit);
    loop.exec();
}
class Service : public QDBusVirtualObject
{
    QMap<QString, int> requests;
public:
    QString introspect(const QString &) const override { return {}; }
    bool handleMessage(const QDBusMessage &m, const QDBusConnection &bus) override
    {
        m.setDelayedReply(true);
        if (m.member() != "GetConfigPath") return true;
        const int count = ++requests[m.path()];
        if (m.path() == "/silent" || (m.path() == "/flaky" && count > 1)) return true;
        const QString path = m.path() == "/empty" ? QString() :
            (count == 1 ? QStringLiteral("/policy/one") : QStringLiteral("/policy/two"));
        if (m.path() == "/delayed" && count == 1) {
            QTimer::singleShot(800, this, [m, bus, path] {
                bus.send(m.createReply(QVariantList{path}));
            });
        } else {
            bus.send(m.createReply(QVariantList{path}));
        }
        return true;
    }
};
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().contains("--service")) {
        Service service;
        auto bus = QDBusConnection::sessionBus();
        for (const QString &path : {"/valid", "/empty", "/silent", "/flaky", "/delayed"})
            require(bus.registerVirtualObject(path, &service));
        require(bus.registerService("org.openkylin.SecurityTest"));
        std::puts("ready"); std::fflush(stdout);
        return app.exec();
    }
    QProcess service;
    service.start(app.applicationFilePath(), {"--service"});
    require(service.waitForStarted());
    require(service.waitForReadyRead(5000));
    require(service.readAllStandardOutput().contains("ready"));
    const auto bus = QDBusConnection::sessionBus();
    const QString name = "org.openkylin.SecurityTest";
    SecurityPathProvider valid(&app, "test", bus, name, "/valid");
    SecurityPathProvider empty(&app, "test", bus, name, "/empty");
    SecurityPathProvider silent(&app, "test", bus, name, "/silent");
    SecurityPathProvider flaky(&app, "test", bus, name, "/flaky");
    SecurityPathProvider delayed(&app, "test", bus, name, "/delayed");
    int success = 0, timeouts = 0, ticks = 0;
    bool emptyReturned = false, destroyedCalled = false, delayedReturned = false;
    QTimer heartbeat;
    QObject::connect(&heartbeat, &QTimer::timeout, &app, [&] { ++ticks; });
    heartbeat.start(10);
    QElapsedTimer elapsed;
    elapsed.start();
    auto successCallback = [&](const QString &path) { require(path == "/policy/one"); ++success; };
    valid.request(successCallback);
    valid.request(successCallback); // Coalesce both consumers into one request.
    empty.request([&](const QString &path) { require(path.isEmpty()); emptyReturned = true; });
    silent.request([&](const QString &path) { require(path.isEmpty()); ++timeouts; });
    flaky.request(successCallback);
    delayed.request([&](const QString &path) { require(path == "/policy/two"); delayedReturned = true; });
    auto *destroyed = new SecurityPathProvider(nullptr, "test", bus, name, "/silent");
    destroyed->request([&](const QString &) { destroyedCalled = true; });
    delete destroyed;
    require(elapsed.elapsed() < 100);
    runFor(300);
    require(success == 3 && emptyReturned && timeouts == 0 && ticks > 1);
    delayed.invalidate(); // The first in-flight result must not override the new lookup.
    flaky.invalidate();
    flaky.request([&](const QString &path) { require(path == "/policy/one"); ++timeouts; });
    runFor(2200);
    require(timeouts == 2 && !destroyedCalled && delayedReturned && ticks > 50);
    valid.request(successCallback); // Cached result, no second backend lookup.
    require(success == 4 && valid.ready() && flaky.ready() && silent.ready());
    service.terminate();
    require(service.waitForFinished());
}
