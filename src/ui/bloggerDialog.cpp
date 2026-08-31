#include "bloggerDialog.h"
#include "ui_bloggerDialog.h"
#include <QMessageBox>
#include <QFileInfo>
#include <QDir>
#include <QCoreApplication>
#include <QProcessEnvironment>
#include <QRegularExpression>

BloggerDialog::BloggerDialog(QWidget *parent, const Blogger &editBlogger)
    : QDialog(parent), ui(new Ui::BloggerDialog), m_original(editBlogger)
{
    ui->setupUi(this);
    setWindowTitle(editBlogger.isValid() ? "编辑博主" : "添加博主");
    setModal(true);
    resize(460, 320);

    ui->comboPlatform->clear();
    ui->comboPlatform->addItem("微信公众号", "wechat");
    ui->comboPlatform->addItem("微博", "weibo");
    ui->comboPlatform->addItem("小红书", "xiaohongshu");

    if (editBlogger.isValid()) {
        setBlogger(editBlogger);
        m_verified = editBlogger.verified;
        ui->labelVerifyStatus->setText(editBlogger.verified ? "✓ 已验证" : "未验证");
        ui->labelVerifyStatus->setStyleSheet(editBlogger.verified ? "color:#10B981;" : "color:#64748B;");
    } else {
        ui->labelVerifyStatus->setText("未验证 · 点击校验真实性");
    }

    connect(ui->btnVerify, &QPushButton::clicked, this, &BloggerDialog::onVerifyClicked);
    connect(ui->comboPlatform, QOverload<int>::of(&QComboBox::currentIndexChanged), this, &BloggerDialog::onPlatformChanged);
    connect(ui->buttonBox, &QDialogButtonBox::accepted, this, [this]{
        if (!validateInput()) return;
        // 若未验证则提醒但允许保存
        if (!m_verified) {
            auto ret = QMessageBox::question(this, "未验证", "该博主尚未通过真实性校验，是否仍保存？\n（建议先点击“校验”）", QMessageBox::Yes|QMessageBox::No);
            if (ret != QMessageBox::Yes) return;
        }
        accept();
    });
    connect(ui->buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

    // 自动生成 ID 提示
    connect(ui->editName, &QLineEdit::textChanged, this, [this]{
        if (ui->editId->text().isEmpty() || ui->editId->text().startsWith("wechat_") || ui->editId->text().startsWith("weibo_") || ui->editId->text().startsWith("xhs_")) {
            ui->editId->setPlaceholderText(generateId(ui->comboPlatform->currentData().toString(), ui->editName->text()));
        }
    });

    onPlatformChanged(ui->comboPlatform->currentIndex());
}

BloggerDialog::~BloggerDialog(){ if(m_verifyProc && m_verifyProc->state()!=QProcess::NotRunning) { m_verifyProc->kill(); } delete ui; }

void BloggerDialog::setBlogger(const Blogger &b)
{
    ui->editName->setText(b.name);
    int idx = ui->comboPlatform->findData(b.platform);
    if (idx>=0) ui->comboPlatform->setCurrentIndex(idx);
    ui->editId->setText(b.id);
    ui->editUrl->setText(b.url);
}

Blogger BloggerDialog::blogger() const
{
    Blogger b;
    b.name = ui->editName->text().trimmed();
    b.platform = ui->comboPlatform->currentData().toString();
    QString id = ui->editId->text().trimmed();
    if (id.isEmpty()) id = generateId(b.platform, b.name);
    b.id = id;
    b.url = ui->editUrl->text().trimmed();
    b.verified = m_verified;
    return b;
}

bool BloggerDialog::validateInput()
{
    if (ui->editName->text().trimmed().isEmpty()) { QMessageBox::warning(this,"提示","请输入博主名称"); ui->editName->setFocus(); return false; }
    QString plat = ui->comboPlatform->currentData().toString();
    if (plat.isEmpty()) { QMessageBox::warning(this,"提示","请选择平台"); return false; }
    QString id = ui->editId->text().trimmed();
    if (id.isEmpty()) id = generateId(plat, ui->editName->text());
    // 简单规则
    if (id.length() < 3) { QMessageBox::warning(this,"提示","ID 过短"); return false; }
    QRegularExpression re("^[a-zA-Z0-9_\\-]+$");
    if (!re.match(id).hasMatch()) { QMessageBox::warning(this,"提示","ID 仅允许字母/数字/下划线/横线"); return false; }
    return true;
}

QString BloggerDialog::generateId(const QString &platform, const QString &name) const
{
    QString base = name.trimmed();
    // 取拼音首字母或直接转 ascii（简化：用随机后缀）
    base.replace(QRegularExpression("[^a-zA-Z0-9]"), "_");
    if (base.isEmpty()) base = "blogger";
    if (base.length()>20) base = base.left(20);
    return QString("%1_%2").arg(platform, base.toLower());
}

void BloggerDialog::onPlatformChanged(int idx)
{
    QString plat = ui->comboPlatform->itemData(idx).toString();
    if (plat=="wechat") {
        ui->editId->setPlaceholderText("如 wechat_li_yongle");
        ui->editUrl->setPlaceholderText("https://mp.weixin.qq.com/s/... 或留空");
    } else if (plat=="weibo") {
        ui->editId->setPlaceholderText("如 weibo_leijun");
        ui->editUrl->setPlaceholderText("https://m.weibo.cn/u/... 或留空");
    } else {
        ui->editId->setPlaceholderText("如 xhs_food_001");
        ui->editUrl->setPlaceholderText("https://www.xiaohongshu.com/user/... 或留空");
    }
}

QString BloggerDialog::pythonExecutable() const
{
    QString envPy = qEnvironmentVariable("PYTHON_EXE");
    if (!envPy.isEmpty() && QFileInfo::exists(envPy)) return envPy;
#ifdef Q_OS_WIN
    return "python";
#else
    return "python3";
#endif
}
QString BloggerDialog::resolveScript(const QString &rel) const
{
    QStringList cands = { QCoreApplication::applicationDirPath()+"/"+rel, QDir::currentPath()+"/"+rel, rel };
    for (auto &p: cands) if (QFileInfo::exists(QDir::cleanPath(p))) return QDir::cleanPath(p);
    return QDir::cleanPath(cands.first());
}

void BloggerDialog::onVerifyClicked()
{
    if (!validateInput()) return;
    Blogger b = blogger();
    ui->btnVerify->setEnabled(false);
    ui->btnVerify->setText("校验中…");
    ui->labelVerifyStatus->setText("正在校验真实性，请稍候…");
    ui->labelVerifyStatus->setStyleSheet("color:#6366F1;");

    QString script = resolveScript("python/crawler/verify_blogger.py");
    // 回退到 crawler.py --verify
    if (!QFileInfo::exists(script)) script = resolveScript("python/crawler/crawler.py");

    if (!QFileInfo::exists(script)) {
        QMessageBox::critical(this,"错误","找不到校验脚本");
        ui->btnVerify->setEnabled(true); ui->btnVerify->setText("校验"); return;
    }

    if (m_verifyProc) { m_verifyProc->deleteLater(); }
    m_verifyProc = new QProcess(this);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING","utf-8");
    m_verifyProc->setProcessEnvironment(env);
    m_verifyProc->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_verifyProc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this, &BloggerDialog::onVerifyFinished);
    connect(m_verifyProc, &QProcess::readyReadStandardOutput, this, &BloggerDialog::onVerifyOutput);

    QStringList args;
    if (script.endsWith("verify_blogger.py")) {
        args << script << "--platform" << b.platform << "--id" << b.id << "--name" << b.name;
        if (!b.url.isEmpty()) args << "--url" << b.url;
    } else {
        args << script << "--blogger" << b.id << "--platform" << b.platform << "--verify";
    }

    m_verifyProc->setWorkingDirectory(QFileInfo(script).absolutePath());
    m_verifyProc->start(pythonExecutable(), args);
    if (!m_verifyProc->waitForStarted(3000)) {
        ui->labelVerifyStatus->setText("启动失败: " + m_verifyProc->errorString());
        ui->labelVerifyStatus->setStyleSheet("color:#EF4444;");
        ui->btnVerify->setEnabled(true); ui->btnVerify->setText("校验");
    }
}

void BloggerDialog::onVerifyOutput()
{
    if (!m_verifyProc) return;
    QString out = QString::fromUtf8(m_verifyProc->readAllStandardOutput()).trimmed();
    if (!out.isEmpty()) ui->labelVerifyStatus->setText(out.left(120));
}

void BloggerDialog::onVerifyFinished(int code, QProcess::ExitStatus st)
{
    Q_UNUSED(st)
    ui->btnVerify->setEnabled(true);
    ui->btnVerify->setText("校验");
    if (code==0) {
        m_verified = true;
        ui->labelVerifyStatus->setText("✓ 校验通过 - 博主真实存在");
        ui->labelVerifyStatus->setStyleSheet("color:#10B981; font-weight:600;");
    } else {
        m_verified = false;
        QString err = m_verifyProc ? QString::fromUtf8(m_verifyProc->readAllStandardOutput()).trimmed() : "";
        if (err.isEmpty()) err = "未找到该博主或校验失败";
        ui->labelVerifyStatus->setText("✗ " + err.left(80));
        ui->labelVerifyStatus->setStyleSheet("color:#EF4444;");
        // 保留选择：仍可保存，但标记未验证
    }
}
