#include "ui.h"
#include <QDesktopServices>
static QString title(QString status) {
    return QMap<QString, QString>{
        {"success", "成功"}, {"partial", "部分完成"}, {"failed", "失敗"}, {"cancelled", "已取消"}}
        .value(status, status);
}
static QPushButton *button(QString text, QWidget *parent = nullptr, bool primary = false) {
    auto b = new QPushButton(text, parent);
    b->setCursor(Qt::PointingHandCursor);
    if (primary)
        b->setProperty("primary", true);
    return b;
}
static QWidget *card() {
    auto w = new QFrame;
    w->setObjectName("card");
    return w;
}
static QLabel *heading(QString text) {
    auto l = new QLabel(text);
    l->setObjectName("heading");
    return l;
}
static void browse(QLineEdit *field) {
    auto p = QFileDialog::getOpenFileName(field, "選擇解壓引擎", {}, "可執行文件 (*.exe)");
    if (!p.isEmpty())
        field->setText(p);
}
FileList::FileList(QWidget *p) : QListWidget(p) {
    setContextMenuPolicy(Qt::CustomContextMenu);
    setSelectionMode(QAbstractItemView::ExtendedSelection);
    connect(this, &QWidget::customContextMenuRequested, this, [this](QPoint p) {
        if (!allowed())
            return;
        QMenu menu;
        auto item = itemAt(p);
        if (item) {
            auto a = menu.addAction("移除文件");
            connect(a, &QAction::triggered, this, [this, item] {
                delete takeItem(row(item));
                changed();
            });
        }
        if (count()) {
            auto a = menu.addAction("清空所有文件");
            connect(a, &QAction::triggered, this, [this] { clearQueue(); });
        }
        menu.exec(viewport()->mapToGlobal(p));
    });
}
QStringList FileList::paths() const {
    QStringList list;
    for (int i = 0; i < count(); ++i)
        list << item(i)->data(Qt::UserRole).toString();
    return list;
}
void FileList::addFiles(QStringList list) {
    if (!allowed())
        return;
    auto current = paths();
    for (auto p : list) {
        p = QFileInfo(p).absoluteFilePath();
        if (QFileInfo(p).isFile() && !current.contains(p)) {
            auto item = new QListWidgetItem(p, this);
            item->setData(Qt::UserRole, p);
            item->setToolTip(p);
            current << p;
        }
    }
    changed();
}
void FileList::clearQueue() {
    if (!allowed())
        return;
    QListWidget::clear();
    changed();
}
DropArea::DropArea(QString text, QWidget *p) : QLabel(text, p) {
    setObjectName("drop");
    setAlignment(Qt::AlignCenter);
    setMinimumHeight(94);
    setAcceptDrops(true);
    setCursor(Qt::PointingHandCursor);
}
void DropArea::dragEnterEvent(QDragEnterEvent *e) {
    if (isEnabled() && e->mimeData()->hasUrls())
        e->acceptProposedAction();
}
void DropArea::dropEvent(QDropEvent *e) {
    if (!isEnabled())
        return;
    QStringList list;
    for (auto u : e->mimeData()->urls())
        if (u.isLocalFile())
            list << u.toLocalFile();
    dropped(list);
    e->acceptProposedAction();
}
void DropArea::mouseReleaseEvent(QMouseEvent *e) {
    if (isEnabled() && e->button() == Qt::LeftButton)
        clicked();
}
ExtractionPanel::ExtractionPanel(bool allInOne, QWidget *parent) : QWidget(parent), all(allInOne) {
    auto outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->setSpacing(0);
    auto scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    auto content = new QWidget;
    auto layout = new QVBoxLayout(content);
    layout->setContentsMargins(28, 26, 28, 24);
    layout->setSpacing(12);
    layout->addWidget(heading(all ? "還原後綴並解壓" : "遞歸解壓"));
    auto row = new QHBoxLayout;
    row->addWidget(new QLabel("解壓引擎"));
    mode = new QComboBox;
    mode->addItems({"自動選擇", "7-Zip", "WinRAR"});
    mode->setMinimumWidth(140);
    row->addWidget(mode);
    extension = new QComboBox;
    extension->addItems({".zip", ".rar", ".7z", ".tar", ".gz"});
    if (all) {
        row->addSpacing(16);
        row->addWidget(new QLabel("真實後綴"));
        row->addWidget(extension);
    } else
        extension->hide();
    row->addStretch();
    auto toolButton = button("工具路徑 ▾");
    row->addWidget(toolButton);
    layout->addLayout(row);
    tools = card();
    auto toolLayout = new QVBoxLayout(tools);
    toolLayout->setContentsMargins(16, 12, 16, 12);
    seven = new QLineEdit;
    rar = new QLineEdit;
    auto s = Settings::load();
    seven->setText(s.seven);
    rar->setText(s.rar);
    for (auto pair : QList<QPair<QString, QLineEdit *>>{{"7-Zip", seven}, {"WinRAR", rar}}) {
        auto r = new QHBoxLayout;
        r->addWidget(new QLabel(pair.first));
        r->addWidget(pair.second, 1);
        auto b = button("瀏覽");
        r->addWidget(b);
        connect(b, &QPushButton::clicked, this, [pair] { browse(pair.second); });
        toolLayout->addLayout(r);
    }
    layout->addWidget(tools);
    tools->hide();
    connect(toolButton, &QPushButton::clicked, this,
            [this] { tools->setVisible(tools->isHidden()); });
    auto drop = new DropArea("拖入壓縮包，或點擊添加文件");
    drop->dropped = [this](QStringList p) { addFiles(p); };
    drop->clicked = [this] {
        addFiles(QFileDialog::getOpenFileNames(this, "添加壓縮包", {}, "所有文件 (*)"));
    };
    layout->addWidget(drop);
    auto queueHeader = new QHBoxLayout;
    count = new QLabel("文件隊列 · 0 個文件");
    queueHeader->addWidget(count);
    queueHeader->addStretch();
    empty = button("清空隊列");
    queueHeader->addWidget(empty);
    layout->addLayout(queueHeader);
    files = new FileList;
    files->setMinimumHeight(120);
    files->allowed = [this] { return !running; };
    files->changed = [this] {
        auto paths = files->paths();
        for (int i = results.size() - 1; i >= 0; --i)
            if (!paths.contains(results[i].source))
                results.removeAt(i);
        count->setText(QString("文件隊列 · %1 個文件").arg(files->count()));
    };
    layout->addWidget(files, 1);
    connect(empty, &QPushButton::clicked, this, &ExtractionPanel::clear);
    auto passCard = card();
    auto passLayout = new QVBoxLayout(passCard);
    passLayout->setContentsMargins(16, 12, 16, 12);
    passLayout->addWidget(new QLabel("Password"));
    password = new QTextEdit;
    password->setPlaceholderText("每行一組密碼，或以逗號分隔");
    password->setFixedHeight(65);
    passLayout->addWidget(password);
    layout->addWidget(passCard);
    detail = new QTextEdit;
    detail->setReadOnly(true);
    detail->setFixedHeight(100);
    detail->hide();
    layout->addWidget(detail);
    scroll->setWidget(content);
    outer->addWidget(scroll, 1);
    auto statusRow = new QHBoxLayout;
    statusRow->setContentsMargins(28, 4, 28, 0);
    auto statusCard = card();
    auto sl = new QVBoxLayout(statusCard);
    sl->setContentsMargins(16, 12, 16, 12);
    auto sr = new QHBoxLayout;
    status = new QLabel("準備就緒");
    status->setWordWrap(true);
    percent = new QLabel("0%");
    percent->setObjectName("muted");
    sr->addWidget(status, 1);
    sr->addWidget(percent);
    sl->addLayout(sr);
    bar = new QProgressBar;
    bar->setRange(0, 100);
    bar->setValue(0);
    bar->setTextVisible(false);
    bar->setFixedHeight(6);
    bar->setAccessibleName("文件隊列處理進度");
    auto barWrap = new QWidget;
    auto bl = new QVBoxLayout(barWrap);
    bl->setContentsMargins(8, 7, 8, 7);
    bl->addWidget(bar);
    sl->addWidget(barWrap);
    activity = new QLabel;
    activity->setObjectName("muted");
    activity->setWordWrap(true);
    activity->hide();
    sl->addWidget(activity);
    statusRow->addWidget(statusCard);
    outer->addLayout(statusRow);
    auto buttons = new QHBoxLayout;
    buttons->setSpacing(8);
    buttons->setContentsMargins(28, 4, 28, 20);
    auto details = button("查看結果");
    open = button("打開結果目錄");
    open->setEnabled(false);
    stop = button("取消任務");
    stop->setEnabled(false);
    begin = button("開始解壓", this, true);
    begin->setMinimumSize(170, 40);
    buttons->addWidget(details);
    buttons->addWidget(open);
    buttons->addStretch();
    buttons->addWidget(stop);
    buttons->addWidget(begin);
    outer->addLayout(buttons);
    connect(details, &QPushButton::clicked, this,
            [this] { detail->setVisible(detail->isHidden()); });
    connect(open, &QPushButton::clicked, this, [this] {
        for (int i = results.size() - 1; i >= 0; --i)
            if (QFileInfo(results[i].output).isDir()) {
                QDesktopServices::openUrl(QUrl::fromLocalFile(results[i].output));
                break;
            }
    });
    connect(begin, &QPushButton::clicked, this, &ExtractionPanel::start);
    connect(stop, &QPushButton::clicked, this, &ExtractionPanel::cancel);
}
void ExtractionPanel::applyPaths(Settings s) {
    if (!running) {
        seven->setText(s.seven);
        rar->setText(s.rar);
    }
}
void ExtractionPanel::addFiles(QStringList p) { files->addFiles(p); }
void ExtractionPanel::clear() {
    if (running)
        return;
    files->clearQueue();
    results.clear();
    bar->setValue(0);
    percent->setText("0%");
    status->setText("準備就緒");
    activity->hide();
    detail->clear();
    detail->hide();
    open->setEnabled(false);
    begin->setText("開始解壓");
}
void ExtractionPanel::setActivity(QString s) {
    activity->setText(s);
    activity->setVisible(!s.isEmpty());
}
void ExtractionPanel::busy(bool value) {
    running = value;
    for (auto w : QList<QWidget *>{files, password, mode, extension, tools, empty})
        w->setEnabled(!value);
    begin->setEnabled(!value);
    stop->setEnabled(value);
    for (auto drop : findChildren<DropArea *>())
        drop->setEnabled(!value);
    begin->setText(value ? "正在解壓…" : "開始解壓");
}
void ExtractionPanel::start() {
    if (running)
        return;
    QStringList originals, sources;
    auto paths = files->paths();
    for (auto p : paths) {
        bool done = false;
        QString source = p;
        for (auto r : results)
            if (r.source == p) {
                done = r.status == "success";
                if (!r.archive.isEmpty())
                    source = r.archive;
            }
        if (!done) {
            originals << p;
            sources << source;
        }
    }
    if (sources.isEmpty()) {
        QMessageBox::information(this, "沒有待處理文件", "請添加文件，或清空隊列後重新導入。");
        return;
    }
    auto s = Settings::load();
    s.seven = seven->text().trimmed();
    s.rar = rar->text().trimmed();
    s.mode = QStringList{"auto", "7z", "winrar"}[mode->currentIndex()];
    bool a = QFileInfo(s.seven).isFile(), b = QFileInfo(s.rar).isFile();
    if ((s.mode == "auto" && !a && !b) || (s.mode == "7z" && !a) || (s.mode == "winrar" && !b)) {
        tools->show();
        QMessageBox::warning(this, "引擎不可用", "請檢查所選引擎的工具路徑。");
        return;
    }
    auto raw = password->toPlainText().replace('\n', ',').replace(QChar(0xff0c), ',');
    QStringList pw;
    for (auto p : raw.split(','))
        if (!p.trimmed().isEmpty())
            pw << p.trimmed();
    engine = std::make_shared<Engine>(s, pw);
    for (int i = results.size() - 1; i >= 0; --i)
        if (results[i].status != "success")
            results.removeAt(i);
    detail->clear();
    bar->setValue(0);
    percent->setText("0%");
    status->setText("正在啟動…");
    setActivity({});
    busy(true);
    auto active = engine;
    QString ext = all ? extension->currentText() : QString();
    active->notify = [this](QString text) {
        QMetaObject::invokeMethod(this, [this, text] { setActivity(text); }, Qt::QueuedConnection);
    };
    thread = QThread::create([this, active, sources, originals, ext] {
        for (int i = 0; i < sources.size(); ++i) {
            if (active->cancelled)
                break;
            QMetaObject::invokeMethod(
                this,
                [this, i, sources] {
                    bar->setValue(i * 100 / sources.size());
                    percent->setText(QString::number(bar->value()) + "%");
                    status->setText(QString("文件隊列 %1/%2").arg(i + 1).arg(sources.size()));
                },
                Qt::QueuedConnection);
            auto r = active->process(sources[i], ext);
            r.source = originals[i];
            QMetaObject::invokeMethod(this, [this, r] { result(r); }, Qt::QueuedConnection);
            if (r.status == "cancelled")
                break;
        }
        if (!active->cancelled)
            QMetaObject::invokeMethod(
                this,
                [this] {
                    bar->setValue(100);
                    percent->setText("100%");
                },
                Qt::QueuedConnection);
    });
    connect(thread, &QThread::finished, this, [this] {
        finish();
        thread->deleteLater();
        thread = nullptr;
    });
    thread->start();
}
void ExtractionPanel::result(Result r) {
    for (int i = results.size() - 1; i >= 0; --i)
        if (results[i].source == r.source)
            results.removeAt(i);
    results << r;
    QString label = title(r.status);
    for (int i = 0; i < files->count(); ++i) {
        auto item = files->item(i);
        if (item->data(Qt::UserRole).toString() == r.source) {
            item->setText("[" + label + "] " + QFileInfo(r.source).fileName());
            item->setToolTip(r.source + "\n" + r.output + "\n" + r.detail);
            item->setForeground(QColor(r.status == "success"   ? "#157333"
                                       : r.status == "partial" ? "#915400"
                                       : r.status == "failed"  ? "#B3261E"
                                                               : "#526174"));
        }
    }
    detail->append(label + " · " + r.source + "\n結果: " + r.output + "\n" + r.detail + "\n");
    for (auto v : results)
        if (!v.output.isEmpty())
            open->setEnabled(true);
}
void ExtractionPanel::cancel() {
    if (running && engine) {
        engine->cancelled = true;
        stop->setEnabled(false);
        setActivity("正在取消…");
    }
}
void ExtractionPanel::finish() {
    busy(false);
    int a = 0, b = 0, c = 0;
    for (auto r : results) {
        a += r.status == "success";
        b += r.status == "partial";
        c += r.status == "failed";
    }
    int pending = files->count() - a - b - c;
    status->setText(
        QString("成功 %1 · 部分完成 %2 · 失敗 %3 · 未完成 %4").arg(a).arg(b).arg(c).arg(pending));
    activity->hide();
    if (b || c || pending) {
        detail->show();
        begin->setText("重試未成功文件");
    }
}
static QIcon navigationIcon(int index) {
    QIcon icon;
    for (bool selected : {false, true}) {
        QPixmap pixmap(28, 28);
        pixmap.fill(Qt::transparent);
        QPainter painter(&pixmap);
        painter.setRenderHint(QPainter::Antialiasing);
        painter.setPen(
            QPen(QColor(selected ? "#007AFF" : "#68717C"), 1.6, Qt::SolidLine, Qt::RoundCap));
        if (index == 0) {
            painter.drawLine(7, 21, 20, 8);
            painter.drawLine(7, 21, 6, 25);
            painter.drawLine(6, 25, 10, 24);
            painter.drawLine(10, 24, 23, 11);
            painter.drawLine(20, 8, 23, 11);
            painter.drawLine(17, 11, 20, 14);
        } else if (index == 1) {
            painter.drawRoundedRect(QRectF(5, 5, 18, 20), 3, 3);
            painter.drawLine(14, 6, 14, 19);
            painter.drawRect(QRectF(12, 19, 4, 4));
            for (int y = 7; y < 18; y += 3)
                painter.drawLine(12, y, 16, y);
        } else if (index == 2) {
            painter.drawArc(QRectF(5, 5, 18, 18), 30 * 16, 130 * 16);
            painter.drawArc(QRectF(5, 5, 18, 18), 210 * 16, 130 * 16);
            painter.drawLine(6, 5, 6, 10);
            painter.drawLine(6, 10, 11, 10);
            painter.drawLine(22, 23, 22, 18);
            painter.drawLine(22, 18, 17, 18);
        } else {
            painter.drawEllipse(QRectF(7, 7, 14, 14));
            painter.drawEllipse(QRectF(11, 11, 6, 6));
            for (int n = 0; n < 8; n++) {
                painter.save();
                painter.translate(14, 14);
                painter.rotate(n * 45);
                painter.drawLine(0, 8, 0, 11);
                painter.restore();
            }
        }
        icon.addPixmap(pixmap, QIcon::Normal, selected ? QIcon::On : QIcon::Off);
    }
    return icon;
}

MainWindow::MainWindow() {
    setWindowTitle("一站式文件解壓助手 v6.1.0");
    resize(1100, 860);
    setMinimumSize(920, 760);
    setWindowIcon(QIcon(QDir(QCoreApplication::applicationDirPath()).filePath("Auto7z.ico")));
    auto root = new QWidget;
    auto l = new QHBoxLayout(root);
    l->setContentsMargins(0, 0, 0, 0);
    l->setSpacing(0);
    auto sidebar = new QWidget;
    sidebar->setObjectName("sidebar");
    sidebar->setFixedWidth(84);
    auto n = new QVBoxLayout(sidebar);
    n->setContentsMargins(8, 12, 8, 12);
    n->setSpacing(8);
    stack = new QStackedWidget;
    pages = {nullptr, nullptr, nullptr, nullptr};
    for (int i = 0; i < 4; ++i) {
        auto placeholder = new QWidget;
        pages[i] = placeholder;
        stack->addWidget(placeholder);
    }
    QStringList names{"一鍵改後綴", "遞歸解壓", "改後綴解壓", "設置"};
    for (int i = 0; i < 4; ++i) {
        if (i == 3)
            n->addStretch();
        auto b = new QToolButton;
        b->setText(names[i]);
        b->setIcon(navigationIcon(i));
        b->setIconSize(QSize(28, 28));
        b->setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
        QFont font = b->font();
        font.setPixelSize(11);
        b->setFont(font);
        b->setCheckable(true);
        b->setMinimumSize(68, 58);
        nav << b;
        n->addWidget(b);
        connect(b, &QToolButton::clicked, this, [this, i] { showPage(i); });
    }
    l->addWidget(sidebar);
    l->addWidget(stack, 1);
    setCentralWidget(root);
    showPage(1);
}
void MainWindow::showPage(int i) {
    if (pages[i]->layout() == nullptr) {
        QWidget *real = nullptr;
        if (i == 0)
            real = changer();
        if (i == 1) {
            extract = new ExtractionPanel;
            real = extract;
        }
        if (i == 2) {
            combined = new ExtractionPanel(true);
            real = combined;
        }
        if (i == 3)
            real = settingsPage();
        auto layout = new QVBoxLayout(pages[i]);
        layout->setContentsMargins(0, 0, 0, 0);
        layout->addWidget(real);
    }
    stack->setCurrentIndex(i);
    for (int j = 0; j < nav.size(); ++j)
        nav[j]->setChecked(j == i);
}
void MainWindow::closeEvent(QCloseEvent *e) {
    bool active = false;
    for (auto p : QList<ExtractionPanel *>{extract, combined})
        if (p && p->running) {
            active = true;
            p->cancel();
        }
    if (active)
        e->ignore();
    else
        e->accept();
}
void MainWindow::snapshot(QString p) { grab().save(p); }
QWidget *MainWindow::changer() {
    auto w = new QWidget;
    auto l = new QVBoxLayout(w);
    l->setContentsMargins(35, 30, 35, 30);
    l->setSpacing(18);
    l->addWidget(heading("一鍵修改文件擴展名"));
    auto drop = new DropArea("🗂 將文件拖拽到此處，或點擊批量選擇");
    drop->setMinimumHeight(140);
    auto list = new FileList;
    drop->dropped = [list](QStringList p) { list->addFiles(p); };
    drop->clicked = [w, list] { list->addFiles(QFileDialog::getOpenFileNames(w, "選擇文件")); };
    l->addWidget(drop);
    l->addWidget(new QLabel("待處理文件列表 (右鍵可移除)："));
    l->addWidget(list, 1);
    auto group = card();
    auto row = new QHBoxLayout(group);
    row->setContentsMargins(15, 12, 15, 12);
    row->addWidget(new QLabel("目標擴展名："));
    auto ext = new QComboBox;
    ext->addItems({".zip", ".rar", ".7z", ".tar", ".gz", ".png", ".mp4"});
    row->addWidget(ext);
    auto empty = button("清空列表");
    row->addWidget(empty);
    row->addStretch();
    auto go = button("開始一鍵修改", w, true);
    row->addWidget(go);
    l->addWidget(group);
    connect(empty, &QPushButton::clicked, list, [list] { list->clearQueue(); });
    connect(go, &QPushButton::clicked, w, [w, list, ext] {
        auto paths = list->paths();
        if (paths.isEmpty()) {
            QMessageBox::information(w, "提示", "請先導入文件！");
            return;
        }
        int good = 0;
        QStringList bad;
        for (auto p : paths) {
            auto f = QFileInfo(p);
            QString target = f.absolutePath() + "/" + f.completeBaseName() + ext->currentText();
            if (p.compare(target, Qt::CaseInsensitive) == 0) {
                good++;
                continue;
            }
            int i = 1;
            while (QFileInfo::exists(target))
                target = f.absolutePath() + "/" + f.completeBaseName() + "_" +
                         QString::number(i++) + ext->currentText();
            if (QFile::rename(p, target))
                good++;
            else
                bad << p;
        }
        list->clearQueue();
        list->addFiles(bad);
        QMessageBox::information(w, "處理結果",
                                 QString("成功 %1 個；未成功 %2 個。").arg(good).arg(bad.size()));
    });
    return w;
}
QWidget *MainWindow::settingsPage() {
    auto scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    auto content = new QWidget;
    auto l = new QVBoxLayout(content);
    l->setContentsMargins(35, 30, 35, 30);
    l->setSpacing(18);
    l->addWidget(heading("程序設置"));
    l->addWidget(new QLabel("修改設置後請點擊下方「保存設置」按鈕使其生效。"));
    auto s = Settings::load();
    auto wait = card();
    auto wl = new QVBoxLayout(wait);
    wl->setContentsMargins(20, 16, 20, 16);
    wl->addWidget(new QLabel("等待與停滯保護"));
    wl->addWidget(new QLabel("解壓默認不限總時長。停滯保護僅在持續無活動時停止；設為 0 可關閉。"));
    auto spin = [&](QVBoxLayout *layout, QString title, QString hint, int value, int min, int max) {
        auto row = new QHBoxLayout;
        auto labels = new QVBoxLayout;
        labels->addWidget(new QLabel(title));
        auto h = new QLabel(hint);
        h->setObjectName("muted");
        h->setWordWrap(true);
        labels->addWidget(h);
        row->addLayout(labels, 1);
        auto input = new QSpinBox;
        input->setRange(min, max);
        input->setValue(value);
        input->setMinimumWidth(100);
        row->addWidget(input);
        layout->addLayout(row);
        return input;
    };
    auto pre =
        spin(wl, "目錄預檢等待（秒）", "超時後直接嘗試解壓，不判定文件失敗。", s.precheck, 3, 300);
    auto idle = spin(wl, "停滯保護（秒，0 = 關閉）", "參考 CPU、工具輸出與文件寫入；慢盤建議關閉。",
                     s.idle, 0, 86400);
    l->addWidget(wait);
    auto paths = card();
    auto pl = new QVBoxLayout(paths);
    pl->setContentsMargins(20, 16, 20, 16);
    pl->addWidget(new QLabel("工具路徑"));
    pl->addWidget(new QLabel("設置後將作為解壓頁面的默認路徑。留空則自動查找。"));
    auto seven = new QLineEdit(s.seven), rar = new QLineEdit(s.rar);
    for (auto pair : QList<QPair<QString, QLineEdit *>>{{"7z.exe", seven}, {"WinRAR.exe", rar}}) {
        auto row = new QHBoxLayout;
        row->addWidget(new QLabel(pair.first));
        row->addWidget(pair.second, 1);
        auto b = button("瀏覽");
        row->addWidget(b);
        connect(b, &QPushButton::clicked, content, [pair] { browse(pair.second); });
        pl->addLayout(row);
    }
    l->addWidget(paths);
    auto advanced = card();
    auto al = new QVBoxLayout(advanced);
    al->setContentsMargins(20, 16, 20, 16);
    al->addWidget(new QLabel("高級設置"));
    auto depth =
        spin(al, "最大遞歸層數", "最外層為第 1 層，同層多個壓縮包不消耗深度。", s.depth, 1, 100);
    auto remove = new QCheckBox("遞歸解壓後刪除壓縮包（僅內層成功的原包）");
    remove->setChecked(s.deleteInner);
    al->addWidget(remove);
    l->addWidget(advanced);
    auto row = new QHBoxLayout;
    auto reset = button("恢復默認"), save = button("保存設置", content, true);
    row->addWidget(reset);
    row->addStretch();
    row->addWidget(save);
    l->addLayout(row);
    l->addStretch();
    connect(reset, &QPushButton::clicked, content, [=] {
        seven->clear();
        rar->clear();
        pre->setValue(30);
        idle->setValue(0);
        depth->setValue(20);
        remove->setChecked(false);
        QMessageBox::information(content, "已重置", "已恢復為默認設置（尚未保存）。");
    });
    connect(save, &QPushButton::clicked, content, [=] {
        Settings s;
        s.seven = seven->text().trimmed();
        s.rar = rar->text().trimmed();
        s.precheck = pre->value();
        s.idle = idle->value();
        s.depth = depth->value();
        s.deleteInner = remove->isChecked();
        if (s.save()) {
            auto effective = Settings::load();
            if (extract)
                extract->applyPaths(effective);
            if (combined)
                combined->applyPaths(effective);
            QMessageBox::information(content, "已保存", "設置已保存，將在下次解壓任務時生效。");
        } else
            QMessageBox::warning(content, "錯誤", "保存設置失敗，請檢查文件權限。");
    });
    scroll->setWidget(content);
    return scroll;
}
