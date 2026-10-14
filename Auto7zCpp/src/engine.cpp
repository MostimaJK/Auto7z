#include "engine.h"
#include <stdexcept>
#ifdef Q_OS_WIN
#include <windows.h>
#endif
static void fail(QString text) { throw std::runtime_error(text.toUtf8().constData()); }
static QString settingPath() {
    return qEnvironmentVariable(
        "AUTO7Z_SETTINGS_FILE",
        QDir(QCoreApplication::applicationDirPath()).filePath("settings.json"));
}
static QString locate(QString exe, QString folder) {
    for (QString dir : QStringList{QCoreApplication::applicationDirPath(), QDir::currentPath(),
                                   QDir(QCoreApplication::applicationDirPath()).filePath("../.."),
                                   qEnvironmentVariable("ProgramFiles") + "/" + folder,
                                   qEnvironmentVariable("ProgramFiles(x86)") + "/" + folder}) {
        QString p = QDir(dir).filePath(exe);
        if (QFileInfo(p).isFile())
            return QFileInfo(p).absoluteFilePath();
    }
    return {};
}
QJsonObject Settings::json() const {
    return {{"settings_version", 2},
            {"path_7z", seven},
            {"path_rar", rar},
            {"max_recursion_depth", depth},
            {"idle_timeout_seconds", idle},
            {"timeout_7z_precheck", precheck},
            {"delete_after_extract", deleteInner}};
}
Settings Settings::load() {
    Settings s;
    QFile f(settingPath());
    QJsonObject o;
    if (f.open(QIODevice::ReadOnly))
        o = QJsonDocument::fromJson(f.readAll()).object();
    s.seven = o["path_7z"].toString();
    s.rar = o["path_rar"].toString();
    s.depth = qBound(1, o["max_recursion_depth"].toInt(20), 100);
    s.deleteInner = o["delete_after_extract"].toBool(false);
    if (o["settings_version"].toInt(1) >= 2) {
        s.idle = qBound(0, o["idle_timeout_seconds"].toInt(0), 86400);
        s.precheck = qBound(3, o["timeout_7z_precheck"].toInt(30), 300);
    }
    if (s.seven.isEmpty())
        s.seven = locate("7z.exe", "7-Zip");
    if (s.rar.isEmpty())
        s.rar = locate("WinRAR.exe", "WinRAR");
    return s;
}
bool Settings::save() const {
    QSaveFile f(settingPath());
    if (!f.open(QIODevice::WriteOnly))
        return false;
    f.write(QJsonDocument(json()).toJson());
    return f.commit();
}
Engine::Engine(Settings s, QStringList p) : settings(s) {
    for (auto v : p)
        if (!v.isEmpty() && !passwords.contains(v))
            passwords << v;
}
void Engine::check() {
    if (cancelled)
        throw Cancelled{};
}
static quint64 cpu(qint64 pid) {
#ifdef Q_OS_WIN
    HANDLE h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, DWORD(pid));
    if (!h)
        return 0;
    FILETIME a, b, c, d;
    quint64 value = 0;
    if (GetProcessTimes(h, &a, &b, &c, &d))
        value = (quint64(c.dwHighDateTime) << 32) + c.dwLowDateTime +
                (quint64(d.dwHighDateTime) << 32) + d.dwLowDateTime;
    CloseHandle(h);
    return value;
#else
    Q_UNUSED(pid);
    return 0;
#endif
}
static QString folderActivity(QString folder) {
    quint64 n = 0, size = 0;
    qint64 latest = 0;
    QDirIterator it(folder, QDir::Files | QDir::NoSymLinks, QDirIterator::Subdirectories);
    while (it.hasNext()) {
        it.next();
        auto f = it.fileInfo();
        n++;
        size += f.size();
        latest = qMax(latest, f.lastModified().toMSecsSinceEpoch());
    }
    return QString("%1/%2/%3").arg(n).arg(size).arg(latest);
}
Engine::Run Engine::run(QString exe, QStringList args, QString folder, int limit) {
    check();
    QProcess p;
    p.setProcessChannelMode(QProcess::MergedChannels);
#ifdef Q_OS_WIN
    p.setCreateProcessArgumentsModifier(
        [](QProcess::CreateProcessArguments *a) { a->flags |= CREATE_NO_WINDOW; });
#endif
    p.start(exe, args);
    if (!p.waitForStarted(5000))
        fail("無法啟動解壓引擎：" + p.errorString());
    p.closeWriteChannel();
    QElapsedTimer clock;
    clock.start();
    qint64 last = 0, report = 0, bytes = 0;
    QString previous;
    QByteArray tail;
    auto drain = [&]() {
        auto data = p.readAll();
        bytes += data.size();
        tail += data;
        if (tail.size() > 262144)
            tail = tail.right(262144);
    };
    try {
        while (p.state() != QProcess::NotRunning) {
            check();
            p.waitForReadyRead(50);
            drain();
            auto now = clock.elapsed();
            if (limit && now > limit * 1000)
                fail("目錄預檢超時");
            if (now - report >= 1000) {
                QString current =
                    QString::number(bytes) + "/" + QString::number(cpu(p.processId())) +
                    (settings.idle && !folder.isEmpty() ? "/" + folderActivity(folder) : "");
                if (current != previous) {
                    last = now;
                    previous = current;
                }
                if (settings.idle && !folder.isEmpty() && now - last >= settings.idle * 1000)
                    fail("持續無活動，可關閉停滯保護後重試");
                notify(activity + QString(" · 已用時 %1 秒 · 可取消").arg(now / 1000));
                report = now;
            }
        }
        drain();
        return {p.exitStatus() == QProcess::NormalExit ? p.exitCode() : 255,
                QString::fromUtf8(tail)};
    } catch (...) {
        p.kill();
        p.waitForFinished(5000);
        throw;
    }
}
int Engine::encrypted(QString source) {
    if (!QFileInfo(settings.seven).isFile() || settings.mode == "winrar")
        return -1;
    try {
        activity = "目錄預檢";
        auto r = run(settings.seven, {"l", "-slt", "-sccUTF-8", "-p", "--", source}, {},
                     settings.precheck);
        if (r.code)
            return -1;
        return r.output.contains("Encrypted = +") ? 1 : 0;
    } catch (Cancelled &) {
        throw;
    } catch (std::exception &) {
        notify("預檢未完成，繼續直接解壓");
        return -1;
    }
}
QString Engine::unique(QString path) {
    QString p = path;
    int i = 1;
    while (QFileInfo::exists(p))
        p = path + "_" + QString::number(i++);
    return p;
}
void Engine::discard(QString stage, QString parent) {
    QFileInfo info(stage);
    if (info.isSymLink() || info.absoluteDir().canonicalPath() != QDir(parent).canonicalPath() ||
        !info.fileName().startsWith(".auto7z-"))
        fail("拒絕清理非任務臨時目錄");
    if (!QDir(stage).removeRecursively())
        fail("臨時目錄清理失敗：" + stage);
}
QString Engine::extract(QString source) {
    check();
    QStringList tools;
    if (settings.mode != "winrar" && QFileInfo(settings.seven).isFile())
        tools << "7z";
    if (settings.mode != "7z" && QFileInfo(settings.rar).isFile())
        tools << "winrar";
    if (tools.isEmpty())
        fail("未找到可用解壓引擎");
    int enc = passwords.isEmpty() ? -1 : encrypted(source);
    QStringList candidates = passwords;
    if (!preferred.isEmpty() && candidates.removeAll(preferred))
        candidates.prepend(preferred);
    if (enc == 0)
        candidates.prepend(QString());
    else
        candidates.append(QString());
    QStringList errors;
    for (auto tool : tools)
        for (int index = 0; index < candidates.size(); ++index) {
            check();
            QString pw = candidates[index];
            activity = QFileInfo(source).fileName() + " · " + tool + " · " +
                       (pw.isEmpty() ? "無密碼" : QString("密碼候選 %1").arg(index + 1));
            notify(activity);
            QTemporaryDir temporary(QFileInfo(source).absolutePath() + "/.auto7z-XXXXXX");
            if (!temporary.isValid())
                fail("無法建立臨時目錄");
            temporary.setAutoRemove(false);
            QString stage = temporary.path();
            bool publishFailed = false;
            try {
                QStringList args;
                QString exe;
                if (tool == "7z") {
                    exe = settings.seven;
                    args = {"x", "-o" + stage, "-y", "-bsp1", "-sccUTF-8", "-p" + pw, "--", source};
                } else {
                    exe = settings.rar;
                    args = {"x",
                            "-y",
                            "-o+",
                            "-ibck",
                            "-inul",
                            "-cfg-",
                            pw.isEmpty() ? "-p-" : "-p" + pw,
                            source,
                            QDir::toNativeSeparators(stage) + QDir::separator()};
                }
                auto r = run(exe, args, stage);
                if (r.code == 0) {
                    auto f = QFileInfo(source);
                    QString target = unique(f.absolutePath() + "/" + f.completeBaseName());
                    if (!QDir().rename(stage, target)) {
                        publishFailed = true;
                        fail("解壓已完成但無法移動結果，文件保留在 " + stage);
                    }
                    if (!pw.isEmpty())
                        preferred = pw;
                    return target;
                }
                for (auto secret : passwords)
                    r.output.replace(secret, "[密碼]");
                errors << tool + QString(" 返回 %1: ").arg(r.code) + r.output.right(400);
                discard(stage, QFileInfo(source).absolutePath());
                if (QList<int>{7, 8, 9, 255}.contains(r.code))
                    break;
            } catch (...) {
                if (!publishFailed && QFileInfo::exists(stage))
                    discard(stage, QFileInfo(source).absolutePath());
                throw;
            }
        }
    fail(errors.join("\n"));
    return {};
}
bool Engine::isArchive(QString path) {
    auto n = QFileInfo(path).fileName().toLower();
    QRegularExpression part("\\.part\\d+\\.rar$");
    if (part.match(n).hasMatch())
        return QRegularExpression("\\.part0*1\\.rar$").match(n).hasMatch();
    return QStringList{"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"}.contains(
               QFileInfo(n).suffix()) ||
           n.endsWith(".7z.001") || n.endsWith(".zip.001");
}
QStringList Engine::scan(QString folder) {
    QStringList found;
    QDirIterator it(folder, QDir::Files | QDir::NoSymLinks, QDirIterator::Subdirectories);
    while (it.hasNext()) {
        QString p = it.next();
        if (isArchive(p))
            found << p;
    }
    found.sort();
    return found;
}
Result Engine::process(QString source, QString ext) {
    source = QFileInfo(source).absoluteFilePath();
    QString current = source, output;
    Result result{source, "failed", {}, {}, source};
    try {
        check();
        auto f = QFileInfo(current);
        if (!ext.isEmpty() && "." + f.suffix().toLower() != ext.toLower()) {
            QString target = f.absolutePath() + "/" + f.completeBaseName() + ext;
            if (QFileInfo::exists(target))
                fail("目標後綴文件已存在，請先處理同名文件");
            if (!QFile::rename(current, target))
                fail("無法還原後綴");
            current = target;
        }
        output = extract(current);
        QList<QPair<QString, int>> queue;
        for (auto p : scan(output))
            queue.append({p, 2});
        QStringList issues;
        while (!queue.isEmpty()) {
            check();
            auto item = queue.takeFirst();
            if (item.second > settings.depth) {
                issues << QString("達到 %1 層上限，保留 %2")
                              .arg(settings.depth)
                              .arg(QFileInfo(item.first).fileName());
                continue;
            }
            try {
                notify(QString("第 %1 層 · ").arg(item.second) + QFileInfo(item.first).fileName());
                QString dir = extract(item.first);
                for (auto p : scan(dir))
                    queue.append({p, item.second + 1});
                if (settings.deleteInner && !QFile::remove(item.first))
                    fail("無法刪除內層原包");
            } catch (Cancelled &) {
                throw;
            } catch (std::exception &e) {
                issues << QFileInfo(item.first).fileName() + ": " + QString::fromUtf8(e.what());
            }
        }
        result = {source, issues.isEmpty() ? "success" : "partial", output, issues.join("\n"),
                  current};
    } catch (Cancelled &) {
        result = {source, "cancelled", output, "已取消；已完成的結果保留",
                  output.isEmpty() ? source : current};
    } catch (std::exception &e) {
        result = {source, "failed", output, QString::fromUtf8(e.what()),
                  output.isEmpty() ? source : current};
    }
    if (output.isEmpty() && current != source && QFileInfo::exists(current) &&
        !QFileInfo::exists(source) && !QFile::rename(current, source)) {
        result.archive = current;
        result.detail += "\n原名還原失敗，原包保留在 " + current;
    }
    return result;
}
