#include "ntpdateprovider.h"
#include <QElapsedTimer>
#include <QEventLoop>
#include <cstdlib>

static void require(bool condition)
{
    if (!condition)
        std::abort();
}

static void runFor(int milliseconds)
{
    QEventLoop loop;
    QTimer::singleShot(milliseconds, &loop, &QEventLoop::quit);
    loop.exec();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QUdpSocket server;
    require(server.bind(QHostAddress(QHostAddress::LocalHost), quint16(0)));
    NtpDateProvider provider(nullptr, QStringLiteral("127.0.0.1"), server.localPort());
    int requests = 0;
    QObject::connect(&server, &QUdpSocket::readyRead, &app, [&] {
        QByteArray request(48, '\0');
        QHostAddress peer;
        quint16 port;
        require(server.readDatagram(request.data(), request.size(), &peer, &port) == 48);
        ++requests;
        QByteArray response(48, '\0');
        response[0] = 0x24;
        response[1] = 2;
        qToBigEndian<quint32>(quint32(1794000000LL + 2208988800LL),
                            reinterpret_cast<uchar *>(response.data() + 40));
        // An unmatched reply must not poison the cached date.
        server.writeDatagram(response, peer, port);
        QTimer::singleShot(50, &app, [&, response, request, peer, port]() mutable {
            require(provider.value().isEmpty());
            response.replace(24, 8, request.mid(40, 8));
            server.writeDatagram(response, peer, port);
        });
    });
    QElapsedTimer elapsed;
    elapsed.start();
    require(provider.value().isEmpty());
    require(elapsed.elapsed() < 100);
    runFor(200);
    require(!provider.value().isEmpty());
    require(requests == 1);
    require(provider.value() == QLocale::c().toString(QDateTime::fromSecsSinceEpoch(1794000000),
                                                    QStringLiteral("ddd MMM d HH:mm:ss yyyy")));

    // A silent server must not stop event processing or trigger repeated lookups.
    QUdpSocket silent;
    require(silent.bind(QHostAddress(QHostAddress::LocalHost), quint16(0)));
    NtpDateProvider offline(nullptr, QStringLiteral("127.0.0.1"), silent.localPort());
    int ticks = 0;
    QTimer heartbeat;
    QObject::connect(&heartbeat, &QTimer::timeout, &app, [&] { ++ticks; });
    heartbeat.start(10);
    elapsed.restart();
    require(offline.value().isEmpty());
    require(elapsed.elapsed() < 100);
    runFor(2300);
    require(ticks > 50);
    require(offline.value().isEmpty());
    require(silent.hasPendingDatagrams());
    char packet[48];
    silent.readDatagram(packet, sizeof(packet));
    runFor(100);
    require(!silent.hasPendingDatagrams());
    return 0;
}
