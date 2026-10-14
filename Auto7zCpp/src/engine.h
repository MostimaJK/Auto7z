#pragma once
#include <QtCore>
#include <atomic>
#include <functional>
struct Settings {
    QString seven, rar, mode = "auto";
    int depth = 20, idle = 0, precheck = 30;
    bool deleteInner = false;
    static Settings load();
    bool save() const;
    QJsonObject json() const;
};
struct Result {
    QString source, status, output, detail, archive;
    QJsonObject json() const {
        return {{"source", source},
                {"status", status},
                {"output", output},
                {"detail", detail},
                {"archive", archive}};
    }
};
struct Cancelled {};
class Engine {
  public:
    Settings settings;
    QStringList passwords;
    QString preferred, activity;
    std::atomic_bool cancelled{false};
    std::function<void(QString)> notify = [](QString) {};
    Engine(Settings s, QStringList p = {});
    Result process(QString source, QString extension = {});
    static bool isArchive(QString path);
    static QStringList scan(QString folder);
    static QString unique(QString path);

  private:
    friend class EngineTests;
    struct Run {
        int code;
        QString output;
    };
    void check();
    Run run(QString program, QStringList args, QString folder = {}, int limit = 0);
    QString extract(QString source);
    int encrypted(QString source);
    void discard(QString stage, QString parent);
};
