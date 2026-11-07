#pragma once
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QObject>
#include <QString>
#include <functional>
#include <utility>
#include <vector>

// Policy lookup must never block construction or the session service event loop.
// Keep the last successful path through a transient backend failure.
class SecurityPathProvider : public QObject
{
public:
    using Callback = std::function<void(const QString &)>;
    explicit SecurityPathProvider(QObject *parent, const QString &user,
        const QDBusConnection &bus = QDBusConnection::systemBus(),
        const QString &service = QStringLiteral("com.kylin.ukui.SettingsDaemon"),
        const QString &path = QStringLiteral("/securityConfig"))
        : QObject(parent), m_user(user), m_service(service), m_objectPath(path), m_bus(bus) {}

    bool ready() const { return m_ready; }
    const QString &currentPath() const { return m_path; }
    void invalidate() { m_ready = false; ++m_generation; }

    void request(Callback callback)
    {
        if (m_ready) { callback(m_path); return; }
        m_callbacks.push_back(std::move(callback));
        if (m_pending) return;
        m_pending = true;
        const unsigned generation = m_generation;
        auto message = QDBusMessage::createMethodCall(m_service, m_objectPath,
            QStringLiteral("com.kylin.ukui.SettingsDaemon.interface"), QStringLiteral("GetConfigPath"));
        message << m_user << QStringLiteral("ukui-control-center");
        auto *watcher = new QDBusPendingCallWatcher(m_bus.asyncCall(message, 1500), this);
        connect(watcher, &QDBusPendingCallWatcher::finished, this,
            [this, watcher, generation](QDBusPendingCallWatcher *) {
                if (generation != m_generation) {
                    m_pending = false;
                    watcher->deleteLater();
                    request([](const QString &) {});
                    return;
                }
                QDBusPendingReply<QString> reply = *watcher;
                if (!reply.isError()) m_path = reply.value();
                m_ready = true;
                m_pending = false;
                auto callbacks = std::move(m_callbacks);
                m_callbacks.clear();
                // A callback may invalidate/request again: all this batch gets
                // the same resolved path, not a value mutated by another callback.
                const QString resolved = m_path;
                watcher->deleteLater();
                for (const auto &callback : callbacks) callback(resolved);
            });
    }
private:
    QString m_user, m_service, m_objectPath, m_path;
    QDBusConnection m_bus;
    bool m_ready = false, m_pending = false;
    unsigned m_generation = 0;
    std::vector<Callback> m_callbacks;
};
