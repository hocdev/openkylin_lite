#include "aboutasync.h"
#include <QCoreApplication>
#include <QDBusVirtualObject>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QProcess>
#include <QTimer>
#include <cstdio>
#include <cstdlib>
#include <functional>

static void require(bool ok) { if (!ok) std::abort(); }
static void runFor(int ms)
{
    QEventLoop loop;
    QTimer::singleShot(ms, &loop, &QEventLoop::quit);
    loop.exec();
}

// Run in a second process so Qt cannot optimise calls to a local object.
class Service : public QDBusVirtualObject
{
public:
    QString introspect(const QString &) const override { return {}; }
    bool handleMessage(const QDBusMessage &message, const QDBusConnection &bus) override
    {
        message.setDelayedReply(true);
        if (message.member() == "Value")
            bus.send(message.createReply(QVariantList{QStringLiteral("ready")}));
        else if (message.member() == "BadType")
            bus.send(message.createReply(QVariantList{42}));
        // Silent deliberately never replies, including to Introspect.
        return true;
    }
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().contains("--service")) {
        Service service;
        auto bus = QDBusConnection::sessionBus();
        require(bus.registerVirtualObject("/", &service));
        require(bus.registerService("org.openkylin.AboutTest"));
        std::puts("ready");
        std::fflush(stdout);
        return app.exec();
    }
    QProcess service;
    service.start(app.applicationFilePath(), {"--service"});
    require(service.waitForStarted());
    require(service.waitForReadyRead(5000));
    require(service.readAllStandardOutput().contains("ready"));
    auto bus = QDBusConnection::sessionBus();
    auto query = [&](QObject *context, const QString &method,
                     std::function<void(bool, const QString &)> callback) {
        queryAbout<QString>(context, bus, "org.openkylin.AboutTest", "/",
            "org.openkylin.AboutTest", method, {}, callback);
    };
    bool value = false, badType = false, timedOut = false, destroyedCalled = false;
    int ticks = 0;
    QTimer heartbeat;
    QObject::connect(&heartbeat, &QTimer::timeout, &app, [&] { ++ticks; });
    heartbeat.start(10);
    QElapsedTimer elapsed;
    elapsed.start();
    query(&app, "Value", [&](bool ok, const QString &v) { value = ok && v == "ready"; });
    query(&app, "BadType", [&](bool ok, const QString &v) { badType = !ok && v.isEmpty(); });
    query(&app, "Silent", [&](bool ok, const QString &v) {
        timedOut = !ok && v.isEmpty();
    });
    auto *context = new QObject;
    query(context, "Silent", [&](bool, const QString &) { destroyedCalled = true; });
    delete context;
    require(elapsed.elapsed() < 100);
    runFor(300);
    require(value && badType && !timedOut && ticks > 5);
    runFor(2400);
    require(timedOut && !destroyedCalled && ticks > 50);
    service.terminate();
    require(service.waitForFinished());
}
