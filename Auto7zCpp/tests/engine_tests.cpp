#include "engine.h"
#include <QtTest>
#include <thread>
class EngineTests : public QObject {
    Q_OBJECT
  private slots:
    void identifiesVolumes() {
        QVERIFY(Engine::isArchive("a.part1.rar"));
        QVERIFY(!Engine::isArchive("a.part2.rar"));
        QVERIFY(Engine::isArchive("a.7z.001"));
        QVERIFY(!Engine::isArchive("a.7z.002"));
    }
    void cleanupRefusesUserFolder() {
        QTemporaryDir parent;
        QDir(parent.path()).mkdir("keep");
        Engine engine(Settings{});
        bool caught = false;
        try {
            engine.discard(parent.path() + "/keep", parent.path());
        } catch (std::exception &) {
            caught = true;
        }
        QVERIFY(caught);
        QVERIFY(QFileInfo::exists(parent.path() + "/keep"));
    }
    void waitsPastOldTimeout() {
        Engine engine(Settings{});
        auto result = engine.run(QCoreApplication::applicationFilePath(), {"--slow-child", "5500"});
        QCOMPARE(result.code, 0);
        QVERIFY(result.output.contains("done"));
    }
    void cancelsOnlyOwnProcess() {
        QProcess unrelated;
        unrelated.start(QCoreApplication::applicationFilePath(), {"--slow-child", "10000"});
        QVERIFY(unrelated.waitForStarted());
        Engine engine(Settings{});
        std::thread timer([&] {
            std::this_thread::sleep_for(std::chrono::milliseconds(300));
            engine.cancelled = true;
        });
        bool caught = false;
        try {
            engine.run(QCoreApplication::applicationFilePath(), {"--slow-child", "10000"});
        } catch (Cancelled &) {
            caught = true;
        }
        timer.join();
        QVERIFY(caught);
        QVERIFY(unrelated.state() != QProcess::NotRunning);
        unrelated.kill();
        unrelated.waitForFinished();
    }
    void idleOptIn() {
        Settings s;
        s.idle = 1;
        Engine engine(s);
        QTemporaryDir stage;
        bool caught = false;
        try {
            engine.run(QCoreApplication::applicationFilePath(), {"--slow-child", "10000"},
                       stage.path());
        } catch (std::exception &) {
            caught = true;
        }
        QVERIFY(caught);
    }
};
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    auto args = app.arguments();
    if (args.contains("--slow-child")) {
        QThread::msleep(args.last().toUInt());
        QFile out;
        out.open(stdout, QIODevice::WriteOnly);
        out.write("done");
        return 0;
    }
    EngineTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "engine_tests.moc"
