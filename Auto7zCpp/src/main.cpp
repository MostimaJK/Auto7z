#include "ui.h"
#include <chrono>
#include <thread>
int main(int argc, char **argv) {
    QStringList args;
    for (int i = 1; i < argc; ++i)
        args << QString::fromLocal8Bit(argv[i]);
    if (args.contains("--engine")) {
        QCoreApplication app(argc, argv);
        args = app.arguments().mid(1);
        QFile input(args.value(args.indexOf("--engine") + 1));
        if (!input.open(QIODevice::ReadOnly))
            return 2;
        auto o = QJsonDocument::fromJson(input.readAll()).object();
        Settings s = Settings::load();
        s.seven = o["path_7z"].toString(s.seven);
        s.rar = o["path_rar"].toString(s.rar);
        s.mode = o["mode"].toString("auto");
        s.depth = o["depth"].toInt(20);
        s.deleteInner = o["delete_inner"].toBool(false);
        s.idle = o["idle"].toInt(0);
        s.precheck = o["precheck"].toInt(30);
        QStringList pw;
        for (auto v : o["passwords"].toArray())
            pw << v.toString();
        Engine engine(s, pw);
        int cancel = o["cancel_after_ms"].toInt(0);
        std::atomic_bool done{false};
        std::thread timer;
        if (cancel)
            timer = std::thread([&] {
                for (int elapsed = 0; elapsed < cancel && !done; elapsed += 10)
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                if (!done)
                    engine.cancelled = true;
            });
        QJsonArray results;
        for (auto v : o["sources"].toArray()) {
            if (engine.cancelled)
                break;
            results.append(engine.process(v.toString(), o["extension"].toString()).json());
        }
        done = true;
        if (timer.joinable())
            timer.join();
        QFile output(args.value(args.indexOf("--engine") + 2));
        if (!output.open(QIODevice::WriteOnly))
            return 3;
        output.write(QJsonDocument(results).toJson());
        return 0;
    }
    QApplication app(argc, argv);
    args = app.arguments().mid(1);
    app.setFont(QFont("Microsoft JhengHei UI", 10));
    QTranslator translator;
    if (translator.load("qtbase_zh_TW",
                        QDir(QCoreApplication::applicationDirPath()).filePath("translations")))
        app.installTranslator(&translator);
    app.setStyleSheet(
        R"(QMainWindow,QWidget {color:#1F2937;font-family:'Microsoft JhengHei UI';} QMainWindow,QStackedWidget,QScrollArea>QWidget>QWidget {background:#F0F0F0;} QWidget#sidebar {background:#F7F9FC;} QFrame#card {background:#FFFFFF;border:1px solid #E5E5EA;border-radius:8px;} QLabel#heading {font-size:24px;font-weight:600;} QLabel#muted {color:#526174;font-size:12px;} QLabel#drop {background:#F1F5FC;border:1.5px dashed #738399;border-radius:12px;font-size:20px;} QPushButton {background:white;border:1px solid #DADDE2;border-radius:6px;padding:7px 12px;min-height:18px;} QPushButton:hover {background:#F7F9FC;} QPushButton[primary=true] {background:#1765CC;color:white;border-color:#1765CC;} QPushButton:disabled {color:#A2A8B2;background:#FAFAFB;} QToolButton {border:none;border-radius:6px;background:transparent;color:#526174;} QToolButton:checked {background:white;color:#007AFF;} QComboBox,QLineEdit,QSpinBox {background:white;border:1px solid #DADDE2;border-radius:6px;padding:6px;} QListWidget,QTextEdit {background:white;border:1px solid #DADDE2;border-radius:8px;padding:8px;} QProgressBar {background:#E5E5EA;border:none;border-radius:3px;} QProgressBar::chunk {background:#007AFF;border-radius:3px;} QScrollArea {border:none;background:transparent;})");
    MainWindow w;
    w.show();
    if (args.contains("--snapshot")) {
        QString p = args.value(args.indexOf("--snapshot") + 1);
        int page = args.value(args.indexOf("--snapshot") + 2, "1").toInt();
        w.showPage(page);
        QTimer::singleShot(200, [&w, &app, p] {
            w.snapshot(p);
            app.quit();
        });
    }
    return app.exec();
}
