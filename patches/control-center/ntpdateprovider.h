// Non-blocking, bounded NTP lookup for the About D-Bus property.
#pragma once

#include <QCoreApplication>
#include <QDateTime>
#include <QHostInfo>
#include <QLocale>
#include <QTimer>
#include <QUdpSocket>
#include <QtEndian>

class NtpDateProvider : public QObject
{
public:
    explicit NtpDateProvider(QObject *parent, const QString &host = QStringLiteral("pool.ntp.org"),
                             quint16 port = 123) : QObject(parent), m_host(host), m_port(port)
    {
        m_timer.setSingleShot(true);
        connect(&m_timer, &QTimer::timeout, this, [this] { finish(); });
        connect(&m_socket, &QUdpSocket::readyRead, this, [this] {
            while (m_socket.hasPendingDatagrams()) {
                QByteArray response(512, '\0');
                const qint64 size = m_socket.readDatagram(response.data(), response.size());
                // Match the response to this request; reject unsynchronised servers.
                if (!m_pending || size < 48 ||
                    (static_cast<unsigned char>(response[0]) & 7) != 4 ||
                    (static_cast<unsigned char>(response[0]) >> 6) == 3 ||
                    static_cast<unsigned char>(response[1]) == 0 ||
                    static_cast<unsigned char>(response[1]) > 15 ||
                    response.mid(24, 8) != m_request.mid(40, 8))
                    continue;
                const quint32 seconds = qFromBigEndian<quint32>(
                    reinterpret_cast<const uchar *>(response.constData() + 40));
                // NTP era 0 wraps in 2036; interpret subsequent dates as era 1.
                const qint64 unixSeconds = seconds < 2208988800U
                    ? qint64(seconds) + 2085978496LL : qint64(seconds) - 2208988800LL;
                m_date = QLocale::c().toString(QDateTime::fromSecsSinceEpoch(unixSeconds),
                                             QStringLiteral("ddd MMM d HH:mm:ss yyyy"));
                finish();
            }
        });
    }

    QString value()
    {
        const qint64 now = QDateTime::currentMSecsSinceEpoch();
        if (!m_pending && now >= m_nextAttempt) {
            m_pending = true;
            m_nextAttempt = now + 15 * 60 * 1000;
            m_date.clear();
            const int generation = ++m_generation;
            m_timer.start(2000); // Includes DNS resolution and the UDP exchange.
            m_lookup = QHostInfo::lookupHost(m_host, this,
                [this, generation](const QHostInfo &info) {
                    if (!m_pending || generation != m_generation)
                        return;
                    m_lookup = -1;
                    if (info.error() != QHostInfo::NoError || info.addresses().isEmpty()) {
                        finish();
                        return;
                    }
                    m_socket.connectToHost(info.addresses().first(), m_port);
                    m_request = QByteArray(48, '\0');
                    m_request[0] = 0x23; // NTP version 4, client mode.
                    const quint64 stamp = (quint64(QDateTime::currentSecsSinceEpoch())
                                           + 2208988800ULL) << 32;
                    qToBigEndian<quint64>(stamp, reinterpret_cast<uchar *>(m_request.data() + 40));
                    if (m_socket.write(m_request) != m_request.size())
                        finish();
                });
        }
        // Existing callers already fall back to local time while this is empty.
        return m_date;
    }

private:
    void finish()
    {
        m_pending = false;
        m_timer.stop();
        if (m_lookup != -1) {
            QHostInfo::abortHostLookup(m_lookup);
            m_lookup = -1;
        }
        m_socket.abort();
    }

    QTimer m_timer;
    QUdpSocket m_socket;
    QByteArray m_request;
    QString m_date;
    QString m_host;
    quint16 m_port;
    qint64 m_nextAttempt = 0;
    int m_lookup = -1;
    int m_generation = 0;
    bool m_pending = false;
};
