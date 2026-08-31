#pragma once
#include <QMainWindow>
#include <QProcess>
#include <QListWidgetItem>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class ProcessRunner;

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    // 顶部筛选
    void onBloggerSelectionChanged();
    void onPlatformFilterChanged(int index);

    // 底部核心流程按钮
    void onBtnCrawlClicked();   // 开始爬取
    void onBtnPolishClicked();  // AI润色 (QProcess演示)
    void onBtnPublishClicked(); // 发布到头条

    // 文章列表
    void onArticleClicked(QListWidgetItem *item);

    // QProcess 回调
    void onPolishFinished(int exitCode, QProcess::ExitStatus status);
    void onPolishError(const QString &msg);
    void onPolishStdout(const QString &text);
    void onPolishStderr(const QString &text);

private:
    void setupConnections();
    void setupBloggerList(); // 初始化博主列表 (Mock数据，预留多平台)
    void setPolishRunning(bool running);
    QString pythonExecutable() const;
    QString resolvePythonScript(const QString &relativePath) const;
    void log(const QString &msg);
    void updateStatus(const QString &msg, int timeout = 0);

    Ui::MainWindow *ui = nullptr;
    QProcess *m_polishProcess = nullptr; // AI润色进程
    QProcess *m_crawlProcess  = nullptr; // 爬虫进程（Step1 预留）
    QString m_tempInPath;
    QString m_tempOutPath;
};
