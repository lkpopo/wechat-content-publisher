#pragma once
#include <QDialog>
#include "core/blogger.h"

QT_BEGIN_NAMESPACE
namespace Ui { class BloggerDialog; }
QT_END_NAMESPACE

// 极简：仅微信号 + 名称，无校验
class BloggerDialog : public QDialog
{
    Q_OBJECT
public:
    explicit BloggerDialog(QWidget *parent = nullptr, const Blogger &editBlogger = {});
    ~BloggerDialog();

    Blogger blogger() const;
    void setBlogger(const Blogger &b);

private:
    bool validateInput();
    Ui::BloggerDialog *ui = nullptr;
    Blogger m_original;
};
