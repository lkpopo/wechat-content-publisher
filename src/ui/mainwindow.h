#pragma once
#include <QMainWindow>
#include <QProcess>
#include <QListWidgetItem>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onBloggerSelectionChanged();
    void onPlatformFilterChanged(int index);
    void onBtnCrawlClicked();
    void onBtnPolishClicked();
    void onBtnPublishClicked();
    void onArticleClicked(QListWidgetItem *item);
    void onThemeToggled();

    // QProcess 回调 - 润色
    void onPolishFinished(int exitCode, QProcess::ExitStatus status);
    void onPolishError(const QString &msg);
    void onPolishStdout(const QString &text);
    void onPolishStderr(const QString &text);
    // QProcess 回调 - 爬取
    void onCrawlFinished(int exitCode, QProcess::ExitStatus status);
    void onCrawlStdout(const QString &text);
    // QProcess 回调 - 发布
    void onPublishFinished(int exitCode, QProcess::ExitStatus status);

private:
    void setupConnections();
    void setupBloggerList();
    void setupUiDetails(); // 现代化细节：阴影、拉伸等

    void setPolishRunning(bool running);
    void setCrawlRunning(bool running);
    void setPublishRunning(bool running);

    QString pythonExecutable() const;
    QString resolvePythonScript(const QString &relativePath) const;
    void log(const QString &msg);
    void updateStatus(const QString &msg, int timeout = 0);
    void refreshArticleListFromJson(const QString &jsonPath);
    void refreshArticleListFromDb(const QString &bloggerId);

    Ui::MainWindow *ui = nullptr;
    QProcess *m_polishProcess = nullptr;
    QProcess *m_crawlProcess  = nullptr;
    QProcess *m_publishProcess = nullptr;
    QString m_tempInPath;
    QString m_tempOutPath;
    QString m_crawlResultPath;
    QString m_publishJsonPath;
};
