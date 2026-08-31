#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QTextStream>
#include <QMessageBox>
#include <QDebug>
#include <QCoreApplication>
#include <QStandardPaths>
#include <QProcessEnvironment>
#include <QScrollBar>

// ================== 构造/析构 ==================
MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    // 窗口标题与初始状态
    setWindowTitle("IwanMoney - 自媒体搬运与发布客户端 v1.0 [Step1]");
    resize(1280, 800);

    // 临时文件路径（与 Python 约定的 IPC 方式：文件交换）
    // 优先使用可执行文件同级目录 data/temp，兼容开发期 currentPath
    QString baseTemp = QCoreApplication::applicationDirPath() + "/data/temp";
    QDir().mkpath(baseTemp);
    m_tempInPath  = baseTemp + "/temp_in.txt";
    m_tempOutPath = baseTemp + "/temp_out.txt";

    setupBloggerList();
    setupConnections();

    // 默认时间段：近7天
    ui->dateEditStart->setDate(QDate::currentDate().addDays(-7));
    ui->dateEditEnd->setDate(QDate::currentDate());
    ui->dateEditStart->setCalendarPopup(true);
    ui->dateEditEnd->setCalendarPopup(true);

    // 双屏编辑器提示
    ui->textEditOriginal->setPlaceholderText("原文内容（左侧）\n\n- 点击左侧文章列表加载原文\n- 或手动粘贴待润色内容\n- 点击「AI润色」将调用 Python 脚本");
    ui->textEditPolished->setPlaceholderText("润色后内容（右侧）\n\n- AI 润色结果将自动显示在此处\n- 可手动二次编辑后点击「发布到头条」");

    // 日志区
    log("[系统] 初始化完成，临时目录: " + baseTemp);
    log("[系统] Python: " + pythonExecutable());
    updateStatus("就绪", 3000);
}

MainWindow::~MainWindow()
{
    if (m_polishProcess) {
        if (m_polishProcess->state() != QProcess::NotRunning) {
            m_polishProcess->kill();
            m_polishProcess->waitForFinished(1000);
        }
    }
    if (m_crawlProcess) {
        if (m_crawlProcess->state() != QProcess::NotRunning) {
            m_crawlProcess->kill();
            m_crawlProcess->waitForFinished(1000);
        }
    }
    delete ui;
}

// ================== 初始化 ==================
void MainWindow::setupBloggerList()
{
    // 预留多平台接口：platform 字段兼容 wechat/weibo/xiaohongshu/toutiao
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
        auto *item = new QListWidgetItem(QString("[%1] %2").arg(b.platform, b.name));
        item->setData(Qt::UserRole, b.id);
        item->setData(Qt::UserRole + 1, b.platform);
        item->setToolTip(QString("ID: %1\n平台: %2").arg(b.id, b.platform));
        ui->listWidgetBloggers->addItem(item);
    }

    // 默认选中第一项
    if (ui->listWidgetBloggers->count() > 0)
        ui->listWidgetBloggers->setCurrentRow(0);

    // 平台筛选下拉
    ui->comboPlatform->clear();
    ui->comboPlatform->addItem("全部平台", "all");
    ui->comboPlatform->addItem("微信公众号", "wechat");
    ui->comboPlatform->addItem("微博", "weibo");
    ui->comboPlatform->addItem("小红书", "xiaohongshu");
}

void MainWindow::setupConnections()
{
    // 顶部筛选
    connect(ui->listWidgetBloggers, &QListWidget::itemSelectionChanged,
            this, &MainWindow::onBloggerSelectionChanged);
    connect(ui->comboPlatform, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &MainWindow::onPlatformFilterChanged);

    // 文章列表
    connect(ui->listWidgetArticles, &QListWidget::itemClicked,
            this, &MainWindow::onArticleClicked);
    connect(ui->listWidgetArticles, &QListWidget::itemDoubleClicked,
            this, &MainWindow::onArticleClicked);

    // 底部按钮 —— 核心流程
    connect(ui->btnCrawl,   &QPushButton::clicked, this, &MainWindow::onBtnCrawlClicked);
    connect(ui->btnPolish,  &QPushButton::clicked, this, &MainWindow::onBtnPolishClicked);
    connect(ui->btnPublish, &QPushButton::clicked, this, &MainWindow::onBtnPublishClicked);

    // 额外：清空/交换按钮（若 UI 存在）
    if (ui->btnClear) {
        connect(ui->btnClear, &QPushButton::clicked, this, [this]{
            ui->textEditOriginal->clear();
            ui->textEditPolished->clear();
            log("[操作] 已清空双屏内容");
        });
    }
    if (ui->btnSwap) {
        connect(ui->btnSwap, &QPushButton::clicked, this, [this]{
            QString a = ui->textEditOriginal->toPlainText();
            ui->textEditOriginal->setPlainText(ui->textEditPolished->toPlainText());
            ui->textEditPolished->setPlainText(a);
            log("[操作] 已交换双屏内容");
        });
    }
}

// ================== 工具方法 ==================
QString MainWindow::pythonExecutable() const
{
    // 1. 优先环境变量 PYTHON_EXE
    QString envPy = qEnvironmentVariable("PYTHON_EXE");
    if (!envPy.isEmpty() && QFileInfo::exists(envPy)) return envPy;

    // 2. 尝试 python / python3
#ifdef Q_OS_WIN
    // Windows 下优先 python
    return "python";
#else
    return "python3";
#endif
}

QString MainWindow::resolvePythonScript(const QString &relativePath) const
{
    // 尝试多个候选路径（兼容开发期与部署期）
    QStringList candidates = {
        QCoreApplication::applicationDirPath() + "/" + relativePath,
        QCoreApplication::applicationDirPath() + "/../" + relativePath,
        QDir::currentPath() + "/" + relativePath,
        QDir::currentPath() + "/../" + relativePath,
        // 源码期直接相对路径
        relativePath
    };
    for (auto &p : candidates) {
        QFileInfo fi(QDir::cleanPath(p));
        if (fi.exists()) return QDir::cleanPath(p);
    }
    // fallback：返回首选（用于报错提示）
    return QDir::cleanPath(candidates.first());
}

void MainWindow::log(const QString &msg)
{
    QString ts = QDateTime::currentDateTime().toString("hh:mm:ss");
    ui->textEditLog->append(QString("[%1] %2").arg(ts, msg));
    auto *bar = ui->textEditLog->verticalScrollBar();
    bar->setValue(bar->maximum());
}

void MainWindow::updateStatus(const QString &msg, int timeout)
{
    ui->statusbar->showMessage(msg, timeout);
}

void MainWindow::setPolishRunning(bool running)
{
    ui->btnPolish->setEnabled(!running);
    ui->btnCrawl->setEnabled(!running);
    ui->progressBar->setVisible(running);
    ui->progressBar->setRange(0, 0); // busy indicator
    if (running) ui->btnPolish->setText("润色中...");
    else ui->btnPolish->setText("AI润色 ▶");
}

// ================== 槽函数：筛选/文章 ==================
void MainWindow::onBloggerSelectionChanged()
{
    auto *item = ui->listWidgetBloggers->currentItem();
    if (!item) return;
    QString id = item->data(Qt::UserRole).toString();
    QString platform = item->data(Qt::UserRole + 1).toString();
    log(QString("[筛选] 选中博主: %1 (平台:%2)").arg(id, platform));

    // Step1 Mock：切换博主时刷新文章列表假数据
    ui->listWidgetArticles->clear();
    for (int i = 1; i <= 5; ++i) {
        QString title = QString("Mock文章 %1 - %2 的示例标题 %3").arg(i).arg(id).arg(QDate::currentDate().toString("MM-dd"));
        auto *aItem = new QListWidgetItem(title);
        aItem->setData(Qt::UserRole, QString("这是博主 %1 的第 %2 篇 Mock 文章正文。\n\n这是第一段，介绍背景。\n这是第二段，阐述观点。\n这是第三段，总结全文。\n\n时间：%3").arg(id).arg(i).arg(QDateTime::currentDateTime().toString(Qt::ISODate)));
        ui->listWidgetArticles->addItem(aItem);
    }
}

void MainWindow::onPlatformFilterChanged(int index)
{
    QString platform = ui->comboPlatform->itemData(index).toString();
    log("[筛选] 平台过滤: " + platform);
    for (int i = 0; i < ui->listWidgetBloggers->count(); ++i) {
        auto *item = ui->listWidgetBloggers->item(i);
        QString p = item->data(Qt::UserRole + 1).toString();
        bool visible = (platform == "all" || p == platform);
        item->setHidden(!visible);
    }
}

void MainWindow::onArticleClicked(QListWidgetItem *item)
{
    if (!item) return;
    QString content = item->data(Qt::UserRole).toString();
    if (content.isEmpty()) content = item->text();
    ui->textEditOriginal->setPlainText(content);
    ui->textEditPolished->clear();
    // 同步标题
    ui->lineEditTitle->setText(item->text().left(40));
    log("[文章] 已加载: " + item->text());
}

// ================== 核心流程：爬取（Step1 Mock） ==================
void MainWindow::onBtnCrawlClicked()
{
    auto *bloggerItem = ui->listWidgetBloggers->currentItem();
    if (!bloggerItem) {
        QMessageBox::warning(this, "提示", "请先选择一个博主");
        return;
    }
    QString bloggerId = bloggerItem->data(Qt::UserRole).toString();
    QDate start = ui->dateEditStart->date();
    QDate end   = ui->dateEditEnd->date();
    if (start > end) {
        QMessageBox::warning(this, "提示", "开始日期不能晚于结束日期");
        return;
    }

    log(QString("[爬取] 开始抓取 博主=%1 时间=%2 至 %3").arg(bloggerId, start.toString(Qt::ISODate), end.toString(Qt::ISODate)));
    updateStatus("正在抓取... (Mock演示)");

    // Step1：暂用 Mock 数据直接填充，不走 Python；Step2 再接 python/crawler/crawler.py
    // 演示 QProcess 调用爬虫的注释骨架：
    /*
    QString script = resolvePythonScript("python/crawler/crawler.py");
    QStringList args = { script, "--blogger", bloggerId, "--start", start.toString("yyyy-MM-dd"), "--end", end.toString("yyyy-MM-dd") };
    m_crawlProcess = new QProcess(this);
    connect(m_crawlProcess, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this, [this](int code, QProcess::ExitStatus st){
        log(QString("[爬取] 进程结束 exit=%1").arg(code));
        // 读取 data/temp/crawl_result.json 并刷新 ui->listWidgetArticles
    });
    m_crawlProcess->start(pythonExecutable(), args);
    */

    // Mock 刷新文章列表
    onBloggerSelectionChanged();
    updateStatus("抓取完成 (Mock 5 篇)", 3000);
    log("[爬取] 完成，已加载 Mock 数据到文章列表");
}

// ================== 核心流程：AI润色（QProcess演示） ==================
void MainWindow::onBtnPolishClicked()
{
    QString original = ui->textEditOriginal->toPlainText().trimmed();
    if (original.isEmpty()) {
        QMessageBox::warning(this, "提示", "左侧原文为空，请输入或选择一篇文章后再润色");
        return;
    }

    // ---- 1. 保存左侧内容到 temp_in.txt (IPC 文件交换) ----
    QFile inFile(m_tempInPath);
    // 确保目录存在
    QDir().mkpath(QFileInfo(m_tempInPath).absolutePath());
    if (!inFile.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
        QMessageBox::critical(this, "错误", "无法写入临时输入文件:\n" + m_tempInPath + "\n" + inFile.errorString());
        return;
    }
    {
        QTextStream ts(&inFile);
        ts.setCodec("UTF-8");
        ts << original;
    }
    inFile.close();
    log(QString("[润色] 已写入 temp_in.txt (%1 字符) -> %2").arg(original.size()).arg(m_tempInPath));

    // ---- 2. 解析 Python 脚本路径 ----
    QString scriptPath = resolvePythonScript("python/automation/ai_polish.py");
    // 回退兼容旧路径 python/ai_polish.py
    if (!QFileInfo::exists(scriptPath)) {
        scriptPath = resolvePythonScript("python/ai_polish.py");
    }
    if (!QFileInfo::exists(scriptPath)) {
        // 最后尝试源码期相对路径
        scriptPath = QDir::cleanPath(QDir::currentPath() + "/python/automation/ai_polish.py");
        if (!QFileInfo::exists(scriptPath))
            scriptPath = QDir::cleanPath(QDir::currentPath() + "/python/ai_polish.py");
    }
    if (!QFileInfo::exists(scriptPath)) {
        QMessageBox::critical(this, "错误", "找不到 ai_polish.py 脚本\n已尝试路径:\n" + scriptPath);
        log("[润色] 错误：找不到 Python 脚本 " + scriptPath);
        return;
    }

    // 清理旧的输出文件
    QFile::remove(m_tempOutPath);

    // ---- 3. QProcess 启动 Python ----
    if (m_polishProcess && m_polishProcess->state() != QProcess::NotRunning) {
        QMessageBox::information(this, "提示", "润色任务正在进行中，请稍候");
        return;
    }
    if (m_polishProcess) {
        m_polishProcess->deleteLater();
    }
    m_polishProcess = new QProcess(this);

    // 关键：合并环境变量，设置 UTF-8
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING", "utf-8");
    m_polishProcess->setProcessEnvironment(env);
    m_polishProcess->setProcessChannelMode(QProcess::MergedChannels);

    connect(m_polishProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &MainWindow::onPolishFinished);
    connect(m_polishProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError){
        onPolishError(m_polishProcess->errorString());
    });
    connect(m_polishProcess, &QProcess::readyReadStandardOutput, this, [this]{
        onPolishStdout(QString::fromUtf8(m_polishProcess->readAllStandardOutput()));
    });
    connect(m_polishProcess, &QProcess::readyReadStandardError, this, [this]{
        onPolishStderr(QString::fromUtf8(m_polishProcess->readAllStandardError()));
    });

    QString pyExe = pythonExecutable();
    QStringList args;
    args << scriptPath << m_tempInPath << m_tempOutPath;

    log(QString("[润色] 启动进程: %1 %2").arg(pyExe, args.join(" ")));
    setPolishRunning(true);
    updateStatus("AI润色中...");

    m_polishProcess->setWorkingDirectory(QFileInfo(scriptPath).absolutePath());
    m_polishProcess->start(pyExe, args);

    if (!m_polishProcess->waitForStarted(5000)) {
        setPolishRunning(false);
        QString err = m_polishProcess->errorString();
        QMessageBox::critical(this, "启动失败", "无法启动 Python 进程:\n" + pyExe + "\n" + err + "\n\n请检查 Python 是否在 PATH，或设置环境变量 PYTHON_EXE");
        log("[润色] 启动失败: " + err);
        return;
    }
    log(QString("[润色] 进程已启动 PID=%1").arg(m_polishProcess->processId()));
}

void MainWindow::onPolishFinished(int exitCode, QProcess::ExitStatus status)
{
    Q_UNUSED(status)
    setPolishRunning(false);

    log(QString("[润色] 进程结束 exitCode=%1 status=%2").arg(exitCode).arg(int(status)));

    if (exitCode != 0) {
        QString errOut = m_polishProcess ? QString::fromUtf8(m_polishProcess->readAllStandardError()) : "";
        QString stdOut = m_polishProcess ? QString::fromUtf8(m_polishProcess->readAllStandardOutput()) : "";
        QMessageBox::warning(this, "润色失败", QString("Python 脚本异常退出 (code=%1)\n%2\n%3").arg(exitCode).arg(stdOut, errOut));
        updateStatus("润色失败", 3000);
        return;
    }

    // ---- 4. 读取 temp_out.txt 显示到右侧 ----
    QFile outFile(m_tempOutPath);
    if (!outFile.exists()) {
        // 回退：尝试从 stdout 读取（若脚本走 stdout 输出）
        QString stdOut = m_polishProcess ? QString::fromUtf8(m_polishProcess->readAllStandardOutput()).trimmed() : "";
        if (!stdOut.isEmpty()) {
            ui->textEditPolished->setPlainText(stdOut);
            log("[润色] 未找到输出文件，已从 stdout 加载结果");
            updateStatus("润色完成 (stdout)", 3000);
            return;
        }
        QMessageBox::warning(this, "润色失败", "未找到输出文件:\n" + m_tempOutPath);
        log("[润色] 失败：输出文件不存在");
        updateStatus("润色失败：无输出文件", 3000);
        return;
    }
    if (!outFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QMessageBox::critical(this, "错误", "无法读取输出文件:\n" + m_tempOutPath);
        return;
    }
    QTextStream ts(&outFile);
    ts.setCodec("UTF-8");
    QString polished = ts.readAll();
    outFile.close();

    ui->textEditPolished->setPlainText(polished);
    log(QString("[润色] 成功，已加载 %1 字符到右侧编辑器").arg(polished.size()));
    updateStatus("润色完成", 3000);
}

void MainWindow::onPolishError(const QString &msg)
{
    setPolishRunning(false);
    log("[润色] 进程错误: " + msg);
    QMessageBox::critical(this, "进程错误", msg);
    updateStatus("润色错误", 3000);
}

void MainWindow::onPolishStdout(const QString &text)
{
    if (!text.trimmed().isEmpty())
        log("[Python stdout] " + text.trimmed().left(500));
}

void MainWindow::onPolishStderr(const QString &text)
{
    if (!text.trimmed().isEmpty())
        log("[Python stderr] " + text.trimmed().left(500));
}

// ================== 核心流程：发布（Step1 预留） ==================
void MainWindow::onBtnPublishClicked()
{
    QString title = ui->lineEditTitle->text().trimmed();
    QString content = ui->textEditPolished->toPlainText().trimmed();
    if (title.isEmpty()) {
        QMessageBox::warning(this, "提示", "请输入标题");
        ui->lineEditTitle->setFocus();
        return;
    }
    if (content.isEmpty()) {
        QMessageBox::warning(this, "提示", "润色后内容为空，无法发布");
        return;
    }

    log(QString("[发布] 准备发布 标题=\"%1\" 内容%2字符").arg(title).arg(content.size()));
    updateStatus("发布流程 (Step1 预留，未接 Playwright)");

    // Step2 将接入：QProcess 启动 python/automation/publisher.py
    /*
    QString script = resolvePythonScript("python/automation/publisher.py");
    QString tmpPublish = QCoreApplication::applicationDirPath() + "/data/temp/publish.json";
    // 将 title/content 写入 publish.json
    QJsonObject obj; obj["title"]=title; obj["content"]=content;
    QFile f(tmpPublish); f.open(...); f.write(QJsonDocument(obj).toJson()); f.close();
    QProcess *pub = new QProcess(this);
    pub->start(pythonExecutable(), {script, tmpPublish});
    */

    QMessageBox::information(this, "发布", "Step1 为骨架演示，发布自动化将在 Step2 接入 Playwright。\n\n当前标题与内容已就绪，可在日志区查看。");
}
