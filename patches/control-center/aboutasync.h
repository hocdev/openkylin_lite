#pragma once
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>

// Raw messages avoid QDBusInterface's synchronous introspection as well.
template<class T, class Callback>
void queryAbout(QObject *context, const QDBusConnection &bus,
                const QString &service, const QString &path,
                const QString &interface, const QString &method,
                const QVariantList &arguments, Callback callback)
{
    auto message = QDBusMessage::createMethodCall(service, path, interface, method);
    message.setArguments(arguments);
    auto *watcher = new QDBusPendingCallWatcher(bus.asyncCall(message, 2000), context);
    QObject::connect(watcher, &QDBusPendingCallWatcher::finished, context,
                     [watcher, callback](QDBusPendingCallWatcher *) {
        QDBusPendingReply<T> reply = *watcher;
        callback(!reply.isError(), reply.isError() ? T() : reply.value());
        watcher->deleteLater();
    });
}

