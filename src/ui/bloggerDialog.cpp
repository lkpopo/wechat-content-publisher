#include "bloggerDialog.h"
#include "ui_bloggerDialog.h"
#include <QMessageBox>
#include <QRegularExpression>

BloggerDialog::BloggerDialog(QWidget *parent, const Blogger &editBlogger)
    : QDialog(parent), ui(new Ui::BloggerDialog), m_original(editBlogger)
{
    ui->setupUi(this);
    setWindowTitle(editBlogger.isValid() ? "编辑公众号" : "添加公众号");
    setModal(true);
    resize(420, 260);

    if (editBlogger.isValid()) {
        setBlogger(editBlogger);
        ui->labelTitle->setText("编辑微信公众号");
    }

    connect(ui->buttonBox, &QDialogButtonBox::accepted, this, [this]{
        if (!validateInput()) return;
        accept();
    });
    connect(ui->buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);
}

BloggerDialog::~BloggerDialog(){ delete ui; }

void BloggerDialog::setBlogger(const Blogger &b)
{
    ui->editId->setText(b.id);
    ui->editName->setText(b.name);
}

Blogger BloggerDialog::blogger() const
{
    Blogger b;
    b.id = ui->editId->text().trimmed().toLower(); // 微信号统一小写
    b.name = ui->editName->text().trimmed();
    b.platform = "wechat";
    b.url = ""; // 不再需要
    b.verified = true; // 不校验，默认视为已验证以便直接爬取
    return b;
}

bool BloggerDialog::validateInput()
{
    QString id = ui->editId->text().trimmed();
    QString name = ui->editName->text().trimmed();
    if (id.isEmpty()) { QMessageBox::warning(this,"提示","请输入微信号，如 ifanr"); ui->editId->setFocus(); return false; }
    if (name.isEmpty()) { QMessageBox::warning(this,"提示","请输入名称，如 爱范儿"); ui->editName->setFocus(); return false; }
    // 微信号规则：字母开头，2-20位，允许字母/数字/_/-
    QRegularExpression re("^[a-zA-Z][a-zA-Z0-9_\\-]{1,19}$");
    if (!re.match(id).hasMatch()) {
        QMessageBox::warning(this,"提示","微信号格式不正确\n需字母开头，2-20位，字母/数字/_/-");
        return false;
    }
    if (name.length() < 1 || name.length() > 30) {
        QMessageBox::warning(this,"提示","名称长度 1-30");
        return false;
    }
    return true;
}
