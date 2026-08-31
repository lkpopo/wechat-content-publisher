#pragma once
#include <QDialog>
#include <QProcess>
#include "core/blogger.h"

QT_BEGIN_NAMESPACE
namespace Ui { class BloggerDialog; }
QT_END_NAMESPACE

// 博主添加/编辑对话框 - 含真实性校验（调用 Python verify）
class BloggerDialog : public QDialog
{
    Q_OBJECT
public:
    explicit BloggerDialog(QWidget *parent = nullptr, const Blogger &editBlogger = {});
    ~BloggerDialog();

    Blogger blogger() const;
    void setBlogger(const Blogger &b);

private slots:
    void onVerifyClicked();
    void onPlatformChanged(int idx);
    void onVerifyFinished(int code, QProcess::ExitStatus st);
    void onVerifyOutput();

private:
    bool validateInput();
    QString generateId(const QString &platform, const QString &name) const;
    QString pythonExecutable() const;
    QString resolveScript(const QString &rel) const;

    Ui::BloggerDialog *ui = nullptr;
    Blogger m_original; // 编辑时原始
    QProcess *m_verifyProc = nullptr;
    bool m_verified = false;
};
