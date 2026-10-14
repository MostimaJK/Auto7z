#include "ui.h"
#include <QtTest>
class UITests : public QObject {
    Q_OBJECT
  private slots:
    void lazyPagesAndCompactLayout() {
        MainWindow w;
        w.resize(920, 760);
        w.show();
        QTest::qWait(100);
        QVERIFY(w.extract);
        QVERIFY(!w.combined);
        QVERIFY(w.pages[3]->layout() == nullptr);
        w.showPage(2);
        QVERIFY(w.combined);
        w.showPage(3);
        QVERIFY(w.pages[3]->layout());
        w.showPage(0);
        QVERIFY(w.pages[0]->layout());
        w.showPage(1);
        auto p = w.extract;
        QVERIFY(p->begin->isVisible());
        QVERIFY(p->bar->isVisible());
        QVERIFY(p->begin->mapTo(&w, QPoint(0, 0)).y() + p->begin->height() <= w.height());
        p->bar->setValue(100);
        p->activity->show();
        p->clear();
        QCOMPARE(p->bar->value(), 0);
        QVERIFY(p->activity->isHidden());
    }
    void resultsRetainedRetryAndSettingsMigration() {
        QTemporaryDir temp;
        QString settings = temp.path() + "/settings.json";
        qputenv("AUTO7Z_SETTINGS_FILE", settings.toUtf8());
        QFile old(settings);
        QVERIFY(old.open(QIODevice::WriteOnly));
        old.write("{\"timeout_no_password\":5,\"timeout_7z_precheck\":3}");
        old.close();
        auto s = Settings::load();
        QCOMPARE(s.precheck, 30);
        QCOMPARE(s.idle, 0);
        s.seven = qEnvironmentVariable("AUTO7Z_TEST_7Z");
        s.rar = "";
        QVERIFY(QFileInfo::exists(s.seven));
        QVERIFY(s.save());
        QFile value(temp.path() + "/value.txt");
        QVERIFY(value.open(QIODevice::WriteOnly));
        value.write("hello");
        value.close();
        QString archive = temp.path() + "/good.zip";
        QProcess zip;
        zip.start(s.seven, {"a", archive, value.fileName()});
        QVERIFY(zip.waitForFinished());
        QCOMPARE(zip.exitCode(), 0);
        QFile bad(temp.path() + "/bad.zip");
        QVERIFY(bad.open(QIODevice::WriteOnly));
        bad.write("invalid");
        bad.close();
        MainWindow w;
        w.show();
        auto p = w.extract;
        p->rar->clear();
        p->addFiles({archive, bad.fileName()});
        p->start();
        QVERIFY(p->running);
        QVERIFY(!p->empty->isEnabled());
        QTRY_VERIFY_WITH_TIMEOUT(!p->running, 15000);
        QCOMPARE(p->results.size(), 2);
        QCOMPARE(p->results[0].status, QString("success"));
        QCOMPARE(p->results[1].status, QString("failed"));
        p->start();
        QTRY_VERIFY_WITH_TIMEOUT(!p->running, 15000);
        QVERIFY(!QFileInfo::exists(temp.path() + "/good_1"));
        p->clear();
        QVERIFY(p->results.isEmpty());
        QVERIFY(!p->open->isEnabled());
        QString disguised = temp.path() + "/partial.png";
        QProcess zip2;
        zip2.start(s.seven, {"a", "-tzip", disguised, bad.fileName()});
        QVERIFY(zip2.waitForFinished());
        w.showPage(2);
        auto all = w.combined;
        all->rar->clear();
        all->addFiles({disguised});
        all->start();
        QTRY_VERIFY_WITH_TIMEOUT(!all->running, 15000);
        QCOMPARE(all->results[0].status, QString("partial"));
        all->start();
        QTRY_VERIFY_WITH_TIMEOUT(!all->running, 15000);
        QCOMPARE(all->results.size(), 1);
        QCOMPARE(all->results[0].source, disguised);
        QVERIFY(QFileInfo::exists(temp.path() + "/partial_1"));
        qunsetenv("AUTO7Z_SETTINGS_FILE");
    }
};
QTEST_MAIN(UITests)
#include "ui_tests.moc"
