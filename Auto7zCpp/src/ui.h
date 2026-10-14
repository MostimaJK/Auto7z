#pragma once
#include "engine.h"
#include <QtWidgets>
#include <memory>
class FileList : public QListWidget {
    Q_OBJECT
    friend class UITests;

  public:
    explicit FileList(QWidget *parent = nullptr);
    QStringList paths() const;
    void addFiles(QStringList paths);
    void clearQueue();
    std::function<void()> changed = []() {};
    std::function<bool()> allowed = []() { return true; };
};
class DropArea : public QLabel {
    Q_OBJECT
    friend class UITests;

  public:
    explicit DropArea(QString text, QWidget *parent = nullptr);
    std::function<void(QStringList)> dropped = [](QStringList) {};
    std::function<void()> clicked = []() {};

  protected:
    void dragEnterEvent(QDragEnterEvent *) override;
    void dropEvent(QDropEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
};
class ExtractionPanel : public QWidget {
    Q_OBJECT
    friend class UITests;

  public:
    explicit ExtractionPanel(bool allInOne = false, QWidget *parent = nullptr);
    bool running = false;
    std::shared_ptr<Engine> engine;
    void addFiles(QStringList);
    void start();
    void cancel();
    void clear();
    void applyPaths(Settings);

  private:
    bool all;
    QComboBox *mode, *extension;
    QLineEdit *seven, *rar;
    QWidget *tools;
    FileList *files;
    QLabel *count, *status, *percent, *activity;
    QTextEdit *password, *detail;
    QProgressBar *bar;
    QPushButton *begin, *stop, *empty, *open;
    QThread *thread = nullptr;
    QList<Result> results;
    void result(Result);
    void finish();
    void busy(bool);
    void setActivity(QString);
};
class MainWindow : public QMainWindow {
    Q_OBJECT
    friend class UITests;

  public:
    MainWindow();
    ExtractionPanel *extract = nullptr, *combined = nullptr;
    void showPage(int);
    void snapshot(QString path);

  protected:
    void closeEvent(QCloseEvent *) override;

  private:
    QStackedWidget *stack;
    QList<QWidget *> pages;
    QList<QToolButton *> nav;
    QWidget *changer();
    QWidget *settingsPage();
};
