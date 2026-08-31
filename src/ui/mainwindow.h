#pragma once
#include <QMainWindow>
#include <QProcess>
#include <QListWidgetItem>
class QTextEdit;

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

    // 博主管理
    void onAddBlogger();
    void onEditBlogger();
    void onDeleteBlogger();
    void onBloggerContextMenu(const QPoint &pos);

    // 快捷操作
    void onBtnOpenArticlesDir();

    // Markdown
    void onMarkdownOriginalToggled(bool checked);
    void onMarkdownPolishedToggled(bool checked);

    // QProcess 回调
    void onPolishFinished(int exitCode, QProcess::ExitStatus status);
    void onPolishError(const QString &msg);
    void onPolishStdout(const QString &text);
    void onPolishStderr(const QString &text);
    void onCrawlFinished(int exitCode, QProcess::ExitStatus status);
    void onCrawlStdout(const QString &text);
    void onPublishFinished(int exitCode, QProcess::ExitStatus status);
    void onDeleteArticle();

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    void setupConnections();
    void setupBloggerList();
    void setupUiDetails();

    void updateWorkflowStep(int step);
    void updateArticleStats();

    void setPolishRunning(bool running);
    void setCrawlRunning(bool running);
    void setPublishRunning(bool running);

    QString pythonExecutable() const;
    QString resolvePythonScript(const QString &relativePath) const;
    void log(const QString &msg);
    void updateStatus(const QString &msg, int timeout = 0);
    void refreshArticleListFromJson(const QString &jsonPath);
    void scaleEditorImages(QTextEdit *edit, qreal factor);

    // Markdown helpers
    void applyMarkdown(QTextEdit *edit, const QString &markdown, bool enable);
    QString m_originalPlain;
    QString m_polishedPlain;
    bool m_originalIsMarkdown = false;
    bool m_polishedIsMarkdown = false;

    bool m_isScanPhase = false;

    Ui::MainWindow *ui = nullptr;
    QProcess *m_polishProcess = nullptr;
    QProcess *m_crawlProcess  = nullptr;
    QProcess *m_publishProcess = nullptr;
    QString m_tempInPath;
    QString m_tempOutPath;
    QString m_crawlResultPath;
    QString m_scanResultPath;
    QString m_selectedTargetsPath;
    QString m_publishJsonPath;
};
