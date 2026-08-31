#include "mainwindow.h"
#include "ui_mainwindow.h"
#include "utils/themeManager.h"
#include "core/database.h"
#include "core/article.h"

#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QTextStream>
#include <QMessageBox>
#include <QDebug>
#include <QCoreApplication>
#include <QProcessEnvironment>
#include <QScrollBar>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QGraphicsDropShadowEffect>
#include <QTimer>

// ================== 构造/析构 ==================
MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    setWindowTitle("IwanMoney — 自媒体搬运与发布客户端 v2.0 [Step2]");
    resize(1320, 860);

    QString baseTemp = QCoreApplication::applicationDirPath() + "/data/temp";
    QDir().mkpath(baseTemp);
    m_tempInPath  = baseTemp + "/temp_in.txt";
    m_tempOutPath = baseTemp + "/temp_out.txt";
    m_crawlResultPath = baseTemp + "/crawl_result.json";
    m_publishJsonPath = baseTemp + "/publish.json";

    setupBloggerList();
    setupConnections();
    setupUiDetails();

    ui->dateEditStart->setDate(QDate::currentDate().addDays(-7));
    ui->dateEditEnd->setDate(QDate::currentDate());
    ui->dateEditStart->setCalendarPopup(true);
    ui->dateEditEnd->setCalendarPopup(true);

    ui->textEditOriginal->setPlaceholderText("在此粘贴原文，或点击左侧文章加载…");
    ui->textEditPolished->setPlaceholderText("AI 润色结果将显示在此处，可二次编辑后发布…");

    // QSplitter 默认比例 1:1
    ui->splitterEditor->setStretchFactor(0, 1);
    ui->splitterEditor->setStretchFactor(1, 1);
    ui->splitterEditor->setSizes({520, 520});

    log("[系统] 初始化完成 v2.0 | 临时目录: " + baseTemp);
    log("[系统] Python: " + pythonExecutable() + " | DB: " + Database::instance().dbPath());
    log("[系统] 主题: " + ThemeManager::instance().themeName() + " (点击右上角切换)");
    updateStatus("就绪 · 选择博主后开始爬取", 4000);
}

MainWindow::~MainWindow()
{
    for (auto *p : {m_polishProcess, m_crawlProcess, m_publishProcess}) {
        if (p && p->state() != QProcess::NotRunning) { p->kill(); p->waitForFinished(1000); }
    }
    delete ui;
}

// ================== UI 细节 ==================
void MainWindow::setupUiDetails()
{
    // 卡片阴影 (现代感)
    auto addShadow = [](QWidget *w, int blur=18, int yOffset=2){
        auto *eff = new QGraphicsDropShadowEffect(w);
        eff->setBlurRadius(blur);
        eff->setOffset(0, yOffset);
        eff->setColor(QColor(15, 23, 42, 28));
        w->setGraphicsEffect(eff);
    };
    // 给 header 与左右面板加阴影（若显存允许）
    if (ui->headerWidget) addShadow(ui->headerWidget, 20, 3);
    // leftPanel/right内卡片已由QSS圆角实现，这里可选阴影
    // 避免对滚动区加阴影导致性能问题，仅对顶层

    // 初始主题按钮文字
    if (ui->btnTheme) {
        ui->btnTheme->setText(ThemeManager::instance().isDark() ? "☀ 浅色" : "🌙 深色");
    }
    // 状态点
    if (ui->labelStatusDot) ui->labelStatusDot->setText("● 就绪");
}

void MainWindow::setupBloggerList()
{
    struct BloggerMock { QString name; QString platform; QString id; };
    QList<BloggerMock> bloggers = {
        {"李永乐老师", "wechat", "wechat_li_yongle"},
        {"半佛仙人",   "wechat", "wechat_banfo"},
        {"雷军",       "weibo",  "weibo_leijun"},
        {"小红书-美食探店", "xiaohongshu", "xhs_food_001"},
        {"Mock-测试博主",  "wechat", "mock_001"},
    };
    ui->listWidgetBloggers->clear();
    for (auto &b : bloggers) {
        // 用小圆点区分平台颜色：wechat绿 weibo橙 xhs粉
        QString dot = b.platform=="wechat" ? "🟢" : b.platform=="weibo" ? "🟠" : "🌸";
        auto *item = new QListWidgetItem(QString("%1 %2  · %3").arg(dot, b.name, b.platform));
        item->setData(Qt::UserRole, b.id);
        item->setData(Qt::UserRole + 1, b.platform);
        item->setToolTip(QString("ID: %1\n平台: %2").arg(b.id, b.platform));
        ui->listWidgetBloggers->addItem(item);
    }
    if (ui->listWidgetBloggers->count() > 0) ui->listWidgetBloggers->setCurrentRow(0);
    ui->comboPlatform->clear();
    ui->comboPlatform->addItem("全部平台", "all");
    ui->comboPlatform->addItem("微信公众号", "wechat");
    ui->comboPlatform->addItem("微博", "weibo");
    ui->comboPlatform->addItem("小红书", "xiaohongshu");
}

void MainWindow::setupConnections()
{
    connect(ui->listWidgetBloggers, &QListWidget::itemSelectionChanged, this, &MainWindow::onBloggerSelectionChanged);
    connect(ui->comboPlatform, QOverload<int>::of(&QComboBox::currentIndexChanged), this, &MainWindow::onPlatformFilterChanged);
    connect(ui->listWidgetArticles, &QListWidget::itemClicked, this, &MainWindow::onArticleClicked);
    connect(ui->listWidgetArticles, &QListWidget::itemDoubleClicked, this, &MainWindow::onArticleClicked);
    connect(ui->btnCrawl,   &QPushButton::clicked, this, &MainWindow::onBtnCrawlClicked);
    connect(ui->btnPolish,  &QPushButton::clicked, this, &MainWindow::onBtnPolishClicked);
    connect(ui->btnPublish, &QPushButton::clicked, this, &MainWindow::onBtnPublishClicked);
    if (ui->btnClear) {
        connect(ui->btnClear, &QPushButton::clicked, this, [this]{
            ui->textEditOriginal->clear(); ui->textEditPolished->clear();
            ui->lineEditTitle->clear(); log("[操作] 已清空双栏");
        });
    }
    if (ui->btnSwap) {
        connect(ui->btnSwap, &QPushButton::clicked, this, [this]{
            QString a = ui->textEditOriginal->toPlainText();
            ui->textEditOriginal->setPlainText(ui->textEditPolished->toPlainText());
            ui->textEditPolished->setPlainText(a);
            log("[操作] 已互换双栏");
        });
    }
    if (ui->btnTheme) {
        connect(ui->btnTheme, &QPushButton::clicked, this, &MainWindow::onThemeToggled);
    }
    connect(&ThemeManager::instance(), &ThemeManager::themeChanged, this, [this](ThemeManager::Theme t){
        if (ui->btnTheme) ui->btnTheme->setText(t==ThemeManager::Dark ? "☀ 浅色" : "🌙 深色");
        log(QString("[主题] 已切换到 %1").arg(t==ThemeManager::Dark?"深色":"浅色"));
    });
}

// ================== 工具 ==================
QString MainWindow::pythonExecutable() const
{
    QString envPy = qEnvironmentVariable("PYTHON_EXE");
    if (!envPy.isEmpty() && QFileInfo::exists(envPy)) return envPy;
#ifdef Q_OS_WIN
    return "python";
#else
    return "python3";
#endif
}
QString MainWindow::resolvePythonScript(const QString &relativePath) const
{
    QStringList candidates = {
        QCoreApplication::applicationDirPath() + "/" + relativePath,
        QCoreApplication::applicationDirPath() + "/../" + relativePath,
        QDir::currentPath() + "/" + relativePath,
        QDir::currentPath() + "/../" + relativePath,
        relativePath
    };
    for (auto &p : candidates) { QFileInfo fi(QDir::cleanPath(p)); if (fi.exists()) return QDir::cleanPath(p); }
    return QDir::cleanPath(candidates.first());
}
void MainWindow::log(const QString &msg)
{
    QString ts = QDateTime::currentDateTime().toString("hh:mm:ss");
    ui->textEditLog->append(QString("[%1] %2").arg(ts, msg));
    auto *bar = ui->textEditLog->verticalScrollBar(); bar->setValue(bar->maximum());
    if (ui->labelStatusDot) ui->labelStatusDot->setText("● " + msg.left(18));
}
void MainWindow::updateStatus(const QString &msg, int timeout){ ui->statusbar->showMessage(msg, timeout); }

void MainWindow::setPolishRunning(bool r){
    ui->btnPolish->setEnabled(!r); ui->btnCrawl->setEnabled(!r); ui->btnPublish->setEnabled(!r);
    ui->progressBar->setVisible(r); ui->progressBar->setRange(0,0);
    ui->btnPolish->setText(r? "润色中…" : "✦  AI 润色");
}
void MainWindow::setCrawlRunning(bool r){
    ui->btnCrawl->setEnabled(!r); ui->btnPolish->setEnabled(!r);
    ui->progressBar->setVisible(r); ui->progressBar->setRange(0,0);
    ui->btnCrawl->setText(r? "抓取中…" : "开始爬取");
}
void MainWindow::setPublishRunning(bool r){
    ui->btnPublish->setEnabled(!r); ui->progressBar->setVisible(r); ui->progressBar->setRange(0,0);
    ui->btnPublish->setText(r? "发布中…" : "发  布");
}

void MainWindow::onThemeToggled()
{
    ThemeManager::instance().toggle();
}

// ================== 模拟旧：筛选 ==================
void MainWindow::onBloggerSelectionChanged()
{
    auto *item = ui->listWidgetBloggers->currentItem(); if (!item) return;
    QString id = item->data(Qt::UserRole).toString();
    QString platform = item->data(Qt::UserRole + 1).toString();
    log(QString("[筛选] 选中 %1 (%2)").arg(id, platform));
    // 优先从 DB 加载历史，否则 Mock
    auto arts = Database::instance().loadArticles(id, 20);
    if (!arts.isEmpty()) {
        ui->listWidgetArticles->clear();
        for (auto &a : arts) {
            auto *it = new QListWidgetItem(a.title);
            it->setData(Qt::UserRole, a.content);
            it->setData(Qt::UserRole+1, a.id);
            it->setToolTip(a.url + "\n" + a.publishTime.toString(Qt::ISODate));
            ui->listWidgetArticles->addItem(it);
        }
        log(QString("[DB] 已加载 %1 篇历史文章").arg(arts.size()));
        return;
    }
    // Mock 填充
    ui->listWidgetArticles->clear();
    for (int i=1;i<=5;++i){
        QString title = QString("Mock %1 - %2 %3").arg(i).arg(id, QDate::currentDate().toString("MM-dd"));
        auto *aItem = new QListWidgetItem(title);
        aItem->setData(Qt::UserRole, QString("博主 %1 第 %2 篇 Mock 正文。\n\n第一段：引入。\n第二段：论述。\n第三段：总结。\n\n%3").arg(id).arg(i).arg(QDateTime::currentDateTime().toString(Qt::ISODate)));
        ui->listWidgetArticles->addItem(aItem);
    }
}
void MainWindow::onPlatformFilterChanged(int index)
{
    QString platform = ui->comboPlatform->itemData(index).toString();
    log("[筛选] 平台: " + platform);
    for (int i=0;i<ui->listWidgetBloggers->count();++i){
        auto *it=ui->listWidgetBloggers->item(i);
        QString p=it->data(Qt::UserRole+1).toString();
        it->setHidden(!(platform=="all"||p==platform));
    }
}
void MainWindow::onArticleClicked(QListWidgetItem *item)
{
    if (!item) return;
    ui->textEditOriginal->setPlainText(item->data(Qt::UserRole).toString());
    ui->textEditPolished->clear();
    ui->lineEditTitle->setText(item->text().left(40));
    log("[文章] 已加载: " + item->text());
}

// ================== Step2：爬取（真实 QProcess） ==================
void MainWindow::onBtnCrawlClicked()
{
    auto *bloggerItem = ui->listWidgetBloggers->currentItem();
    if (!bloggerItem) { QMessageBox::warning(this,"提示","请先选择博主"); return; }
    QString bloggerId = bloggerItem->data(Qt::UserRole).toString();
    QString platform = bloggerItem->data(Qt::UserRole+1).toString();
    QDate start = ui->dateEditStart->date(), end = ui->dateEditEnd->date();
    if (start > end) { QMessageBox::warning(this,"提示","开始日期不能晚于结束日期"); return; }

    QString script = resolvePythonScript("python/crawler/crawler.py");
    if (!QFileInfo::exists(script)) { QMessageBox::critical(this,"错误","找不到 crawler.py: "+script); return; }
    if (m_crawlProcess && m_crawlProcess->state()!=QProcess::NotRunning) { QMessageBox::information(this,"提示","抓取进行中…"); return; }

    log(QString("[爬取] %1 %2 %3~%4").arg(bloggerId, platform, start.toString(Qt::ISODate), end.toString(Qt::ISODate)));
    updateStatus("正在抓取…"); setCrawlRunning(true);
    QFile::remove(m_crawlResultPath);

    if (m_crawlProcess) m_crawlProcess->deleteLater();
    m_crawlProcess = new QProcess(this);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING","utf-8");
    m_crawlProcess->setProcessEnvironment(env);
    m_crawlProcess->setProcessChannelMode(QProcess::MergedChannels);

    connect(m_crawlProcess, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this, &MainWindow::onCrawlFinished);
    connect(m_crawlProcess, &QProcess::readyReadStandardOutput, this, [this]{ onCrawlStdout(QString::fromUtf8(m_crawlProcess->readAllStandardOutput())); });
    connect(m_crawlProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError){ log("[爬取] 进程错误: "+m_crawlProcess->errorString()); setCrawlRunning(false); });

    QStringList args = {script, "--blogger", bloggerId, "--platform", platform, "--start", start.toString("yyyy-MM-dd"), "--end", end.toString("yyyy-MM-dd"), "--output", m_crawlResultPath};
    m_crawlProcess->setWorkingDirectory(QFileInfo(script).absolutePath());
    m_crawlProcess->start(pythonExecutable(), args);
    if (!m_crawlProcess->waitForStarted(5000)) {
        setCrawlRunning(false); QMessageBox::critical(this,"启动失败", m_crawlProcess->errorString()); log("[爬取] 启动失败"); return;
    }
    log(QString("[爬取] PID=%1 已启动").arg(m_crawlProcess->processId()));
}

void MainWindow::onCrawlStdout(const QString &text){
    if (!text.trimmed().isEmpty()) log("[Crawler] " + text.trimmed().left(600));
}

void MainWindow::onCrawlFinished(int exitCode, QProcess::ExitStatus status)
{
    Q_UNUSED(status) setCrawlRunning(false);
    log(QString("[爬取] 结束 code=%1").arg(exitCode));
    if (exitCode!=0) {
        QMessageBox::warning(this,"抓取失败", QString("crawler 退出码 %1\n请查看日志").arg(exitCode));
        updateStatus("抓取失败",3000); return;
    }
    refreshArticleListFromJson(m_crawlResultPath);
}

void MainWindow::refreshArticleListFromJson(const QString &jsonPath)
{
    QFile f(jsonPath);
    if (!f.exists()) { log("[爬取] 结果文件不存在: "+jsonPath); updateStatus("无结果文件",3000); return; }
    if (!f.open(QIODevice::ReadOnly)) { log("[爬取] 无法读取: "+f.errorString()); return; }
    auto doc = QJsonDocument::fromJson(f.readAll());
    f.close();
    QJsonArray arr;
    int count=0;
    if (doc.isObject()) { arr = doc.object().value("articles").toArray(); count = doc.object().value("count").toInt(arr.size()); }
    else if (doc.isArray()) { arr = doc.array(); count = arr.size(); }

    if (arr.isEmpty()) { log("[爬取] 空结果"); updateStatus("抓取完成 0篇",3000); return; }

    QList<Article> articles;
    for (auto v: arr) {
        auto o=v.toObject();
        Article a; a.id=o["id"].toString(); a.title=o["title"].toString(); a.content=o["content"].toString();
        a.platform=o["platform"].toString(); a.bloggerId=o["blogger_id"].toString();
        a.publishTime=QDateTime::fromString(o["publish_time"].toString(), Qt::ISODate);
        if (!a.publishTime.isValid()) a.publishTime=QDateTime::currentDateTime();
        a.url=o["url"].toString(); a.cover=o["cover"].toString();
        // bloggerName 回填
        for(int i=0;i<ui->listWidgetBloggers->count();++i){
            auto *it=ui->listWidgetBloggers->item(i);
            if(it->data(Qt::UserRole).toString()==a.bloggerId) a.bloggerName=it->text();
        }
        articles.append(a);
    }
    // 入库
    Database::instance().saveArticles(articles);
    // 刷新列表
    ui->listWidgetArticles->clear();
    for (auto &a: articles){
        auto *it=new QListWidgetItem(a.title);
        it->setData(Qt::UserRole, a.content);
        it->setData(Qt::UserRole+1, a.id);
        it->setData(Qt::UserRole+2, a.url);
        it->setToolTip(QString("%1\n%2\n%3").arg(a.platform, a.publishTime.toString("yyyy-MM-dd"), a.url));
        ui->listWidgetArticles->addItem(it);
    }
    log(QString("[爬取] 成功 %1 篇，已入库并刷新").arg(count));
    updateStatus(QString("抓取完成 %1 篇").arg(count), 4000);
}

void MainWindow::refreshArticleListFromDb(const QString &bloggerId){
    auto arts = Database::instance().loadArticles(bloggerId);
    ui->listWidgetArticles->clear();
    for(auto &a: arts){ auto *it=new QListWidgetItem(a.title); it->setData(Qt::UserRole,a.content); it->setData(Qt::UserRole+1,a.id); ui->listWidgetArticles->addItem(it); }
}

// ================== AI润色：与 Step1 相同但支持新 UI ==================
void MainWindow::onBtnPolishClicked()
{
    QString original = ui->textEditOriginal->toPlainText().trimmed();
    if (original.isEmpty()) { QMessageBox::warning(this,"提示","左侧原文为空"); return; }
    QFile inFile(m_tempInPath); QDir().mkpath(QFileInfo(m_tempInPath).absolutePath());
    if (!inFile.open(QIODevice::WriteOnly|QIODevice::Truncate|QIODevice::Text)) { QMessageBox::critical(this,"错误","无法写入 temp_in.txt"); return; }
    { QTextStream ts(&inFile); ts.setCodec("UTF-8"); ts<<original; } inFile.close();
    log(QString("[润色] 已写入 %1 字符").arg(original.size()));
    QString scriptPath = resolvePythonScript("python/automation/ai_polish.py");
    if (!QFileInfo::exists(scriptPath)) scriptPath = resolvePythonScript("python/ai_polish.py");
    if (!QFileInfo::exists(scriptPath)) { QMessageBox::critical(this,"错误","找不到 ai_polish.py"); return; }
    QFile::remove(m_tempOutPath);
    if (m_polishProcess && m_polishProcess->state()!=QProcess::NotRunning) { QMessageBox::information(this,"提示","润色进行中…"); return; }
    if (m_polishProcess) m_polishProcess->deleteLater();
    m_polishProcess=new QProcess(this);
    QProcessEnvironment env=QProcessEnvironment::systemEnvironment(); env.insert("PYTHONIOENCODING","utf-8");
    m_polishProcess->setProcessEnvironment(env); m_polishProcess->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_polishProcess, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this, &MainWindow::onPolishFinished);
    connect(m_polishProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError){ onPolishError(m_polishProcess->errorString()); });
    connect(m_polishProcess, &QProcess::readyReadStandardOutput, this, [this]{ onPolishStdout(QString::fromUtf8(m_polishProcess->readAllStandardOutput())); });
    connect(m_polishProcess, &QProcess::readyReadStandardError, this, [this]{ onPolishStderr(QString::fromUtf8(m_polishProcess->readAllStandardError())); });
    QString pyExe=pythonExecutable();
    QStringList args; args<<scriptPath<<m_tempInPath<<m_tempOutPath;
    // Step2：可选额外参数 --provider grok / --mock  (兼容旧脚本忽略未知参数)
    // args << "--provider" << "grok";
    log(QString("[润色] 启动: %1 %2").arg(pyExe, args.join(" ")));
    setPolishRunning(true); updateStatus("AI润色中…");
    m_polishProcess->setWorkingDirectory(QFileInfo(scriptPath).absolutePath());
    m_polishProcess->start(pyExe, args);
    if (!m_polishProcess->waitForStarted(5000)) { setPolishRunning(false); QMessageBox::critical(this,"启动失败",m_polishProcess->errorString()); return; }
    log(QString("[润色] PID=%1").arg(m_polishProcess->processId()));
}
void MainWindow::onPolishFinished(int exitCode, QProcess::ExitStatus status){
    Q_UNUSED(status) setPolishRunning(false);
    log(QString("[润色] 结束 code=%1").arg(exitCode));
    if (exitCode!=0){ QMessageBox::warning(this,"润色失败",QString("退出码 %1").arg(exitCode)); updateStatus("润色失败",3000); return; }
    QFile outFile(m_tempOutPath);
    if (!outFile.exists()){
        QString stdOut = m_polishProcess?QString::fromUtf8(m_polishProcess->readAllStandardOutput()).trimmed():"";
        if(!stdOut.isEmpty()){ ui->textEditPolished->setPlainText(stdOut); updateStatus("润色完成(stdout)",3000); return; }
        QMessageBox::warning(this,"失败","未找到输出文件"); return;
    }
    if(!outFile.open(QIODevice::ReadOnly|QIODevice::Text)) return;
    QTextStream ts(&outFile); ts.setCodec("UTF-8"); QString polished=ts.readAll(); outFile.close();
    ui->textEditPolished->setPlainText(polished);
    log(QString("[润色] 成功 %1 字符").arg(polished.size())); updateStatus("润色完成",3000);
}
void MainWindow::onPolishError(const QString &msg){ setPolishRunning(false); log("[润色] 错误: "+msg); QMessageBox::critical(this,"错误",msg); }
void MainWindow::onPolishStdout(const QString &t){ if(!t.trimmed().isEmpty()) log("[Polish] "+t.trimmed().left(500)); }
void MainWindow::onPolishStderr(const QString &t){ if(!t.trimmed().isEmpty()) log("[Polish] "+t.trimmed().left(500)); }

// ================== 发布：Step2 真实 QProcess ==================
void MainWindow::onBtnPublishClicked()
{
    QString title = ui->lineEditTitle->text().trimmed();
    QString content = ui->textEditPolished->toPlainText().trimmed();
    if (title.isEmpty()){ QMessageBox::warning(this,"提示","请输入标题"); ui->lineEditTitle->setFocus(); return; }
    if (content.isEmpty()){ QMessageBox::warning(this,"提示","润色后内容为空"); return; }
    if (title.size()<5) { if(QMessageBox::question(this,"确认","标题过短，是否继续？")!=QMessageBox::Yes) return; }

    // 写入 publish.json 供 Python 消费
    QJsonObject o; o["title"]=title; o["content"]=content;
    o["platform"]="toutiao"; o["timestamp"]=QDateTime::currentDateTime().toString(Qt::ISODate);
    QDir().mkpath(QFileInfo(m_publishJsonPath).absolutePath());
    QFile f(m_publishJsonPath);
    if (!f.open(QIODevice::WriteOnly|QIODevice::Truncate)) { QMessageBox::critical(this,"错误","无法写入 publish.json"); return; }
    f.write(QJsonDocument(o).toJson()); f.close();
    log(QString("[发布] 已写入 publish.json 标题=%1 %2字").arg(title.left(20)).arg(content.size()));

    QString script = resolvePythonScript("python/automation/publisher.py");
    if (!QFileInfo::exists(script)) { QMessageBox::critical(this,"错误","找不到 publisher.py: "+script); return; }
    if (m_publishProcess && m_publishProcess->state()!=QProcess::NotRunning) { QMessageBox::information(this,"提示","发布进行中…"); return; }
    if (m_publishProcess) m_publishProcess->deleteLater();
    m_publishProcess=new QProcess(this);
    QProcessEnvironment env=QProcessEnvironment::systemEnvironment(); env.insert("PYTHONIOENCODING","utf-8");
    m_publishProcess->setProcessEnvironment(env);
    m_publishProcess->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_publishProcess, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this, &MainWindow::onPublishFinished);
    connect(m_publishProcess, &QProcess::readyReadStandardOutput, this, [this]{ log("[Publish] "+QString::fromUtf8(m_publishProcess->readAllStandardOutput()).trimmed().left(600)); });
    connect(m_publishProcess, &QProcess::readyReadStandardError, this, [this]{ log("[Publish] "+QString::fromUtf8(m_publishProcess->readAllStandardError()).trimmed().left(600)); });

    QStringList args={script, "--input", m_publishJsonPath, "--dry-run"}; // 默认 dry-run，真实发布去掉 --dry-run
    log(QString("[发布] 启动: %1 %2").arg(pythonExecutable(), args.join(" ")));
    setPublishRunning(true); updateStatus("发布中… (dry-run)");
    m_publishProcess->setWorkingDirectory(QFileInfo(script).absolutePath());
    m_publishProcess->start(pythonExecutable(), args);
    if (!m_publishProcess->waitForStarted(5000)) { setPublishRunning(false); QMessageBox::critical(this,"启动失败",m_publishProcess->errorString()); return; }
}

void MainWindow::onPublishFinished(int exitCode, QProcess::ExitStatus status)
{
    Q_UNUSED(status) setPublishRunning(false);
    log(QString("[发布] 结束 code=%1").arg(exitCode));
    if (exitCode==0){
        Database::PublishRecord r;
        r.id = QString::number(QDateTime::currentMSecsSinceEpoch());
        r.title = ui->lineEditTitle->text().trimmed();
        r.platform = "toutiao";
        r.publishTime = QDateTime::currentDateTime();
        r.success = true; r.message="dry-run success";
        Database::instance().savePublishRecord(r);
        updateStatus("发布完成 (dry-run)", 4000);
        QMessageBox::information(this,"发布","已完成发布流程（当前为 dry-run 模拟）。\n去掉 --dry-run 参数即可真实发布。");
    } else {
        updateStatus("发布失败",3000);
        QMessageBox::warning(this,"发布失败",QString("退出码 %1 请查看日志").arg(exitCode));
    }
}
