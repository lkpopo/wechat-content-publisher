#include "crawlSelectionDialog.h"
#include <QCheckBox>
#include <QGraphicsDropShadowEffect>
#include <QDateTime>
#include <QJsonDocument>

CrawlSelectionDialog::CrawlSelectionDialog(const QJsonArray &candidates, const QString &startDate, const QString &endDate, QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("选择要抓取的文章");
    resize(680, 520);
    setMinimumSize(560, 400);
    setupUi(candidates, startDate, endDate);
}

void CrawlSelectionDialog::setupUi(const QJsonArray &candidates, const QString &startDate, const QString &endDate)
{
    auto *rootLayout = new QVBoxLayout(this);
    rootLayout->setContentsMargins(16, 16, 16, 16);
    rootLayout->setSpacing(12);

    // 顶部说明卡片
    auto *topCard = new QWidget(this);
    topCard->setStyleSheet("background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:8px;");
    auto *topLayout = new QVBoxLayout(topCard);
    topLayout->setContentsMargins(10, 8, 10, 8);
    topLayout->setSpacing(4);

    auto *labelTitle = new QLabel(QString("🔍 共扫描到 <b>%1</b> 篇候选文章").arg(candidates.size()), topCard);
    labelTitle->setStyleSheet("font-size:14px; color:#0F172A; font-weight:bold; border:none; background:transparent;");
    auto *labelTip = new QLabel(QString("设定目标时间段：<span style='color:#4F46E5; font-weight:600;'>%1 至 %2</span> （不在时间段内的文章已默认取消勾选）").arg(startDate, endDate), topCard);
    labelTip->setStyleSheet("font-size:12px; color:#64748B; border:none; background:transparent;");

    topLayout->addWidget(labelTitle);
    topLayout->addWidget(labelTip);
    rootLayout->addWidget(topCard);

    // 快捷全选反选操作栏
    auto *toolsLayout = new QHBoxLayout();
    toolsLayout->setSpacing(8);

    auto *btnSelectInRange = new QPushButton("🎯 仅勾选目标时间段", this);
    auto *btnAll = new QPushButton("全选", this);
    auto *btnNone = new QPushButton("全部取消", this);

    QString toolBtnStyle = "QPushButton { background:#FFFFFF; border:1px solid #CBD5E1; border-radius:6px; padding:4px 10px; font-size:11px; } QPushButton:hover { background:#F1F5F9; border-color:#94A3B8; }";
    btnSelectInRange->setStyleSheet(toolBtnStyle + "font-weight:600; color:#4338CA;");
    btnAll->setStyleSheet(toolBtnStyle);
    btnNone->setStyleSheet(toolBtnStyle);

    toolsLayout->addWidget(btnSelectInRange);
    toolsLayout->addWidget(btnAll);
    toolsLayout->addWidget(btnNone);
    toolsLayout->addStretch();

    m_labelCount = new QLabel(this);
    m_labelCount->setStyleSheet("font-size:12px; font-weight:600; color:#334155;");
    toolsLayout->addWidget(m_labelCount);
    rootLayout->addLayout(toolsLayout);

    // 候选文章复选框列表
    m_listWidget = new QListWidget(this);
    m_listWidget->setStyleSheet(
        "QListWidget { background:#FFFFFF; border:1.5px solid #E2E8F0; border-radius:10px; padding:4px; outline:none; } "
        "QListWidget::item { padding:6px 8px; border-bottom:1px solid #F1F5F9; border-radius:6px; margin:2px; } "
        "QListWidget::item:hover { background:#F8FAFC; } "
    );

    for (int i = 0; i < candidates.size(); ++i) {
        auto obj = candidates[i].toObject();
        QString title = obj["title"].toString();
        QString pubTime = obj["publish_time"].toString();
        bool inRange = obj["in_range"].toBool();

        QString displayDate = pubTime.left(10);
        QString displayText = QString("[%1] %2").arg(displayDate, title);
        if (!inRange) {
            displayText += "  (⚠️ 非目标时间段)";
        }

        auto *item = new QListWidgetItem(displayText, m_listWidget);
        item->setFlags(item->flags() | Qt::ItemIsUserCheckable | Qt::ItemIsEnabled);
        // 默认只勾选时间符合区间的文章
        item->setCheckState(inRange ? Qt::Checked : Qt::Unchecked);

        if (!inRange) {
            item->setForeground(QColor("#94A3B8"));
        } else {
            item->setForeground(QColor("#0F172A"));
        }

        // 保存原始完整对象 JSON 字符串
        item->setData(Qt::UserRole, QJsonDocument(obj).toJson(QJsonDocument::Compact));
        item->setData(Qt::UserRole + 1, inRange);
        m_listWidget->addItem(item);
    }
    rootLayout->addWidget(m_listWidget);

    // 底部按钮栏
    auto *bottomLayout = new QHBoxLayout();
    bottomLayout->setSpacing(10);

    auto *btnCancel = new QPushButton("取消", this);
    btnCancel->setStyleSheet("QPushButton { background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:6px 16px; font-size:12px; font-weight:600; color:#475569; } QPushButton:hover { background:#F1F5F9; }");
    btnCancel->setMinimumHeight(34);

    m_btnConfirm = new QPushButton("开始抓取选中文章", this);
    m_btnConfirm->setStyleSheet("QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4F46E5, stop:1 #6366F1); border:none; border-radius:8px; padding:6px 20px; font-size:12px; font-weight:700; color:#FFFFFF; } QPushButton:hover { background:#4338CA; } QPushButton:disabled { background:#CBD5E1; color:#94A3B8; }");
    m_btnConfirm->setMinimumHeight(34);

    bottomLayout->addStretch();
    bottomLayout->addWidget(btnCancel);
    bottomLayout->addWidget(m_btnConfirm);
    rootLayout->addLayout(bottomLayout);

    connect(btnSelectInRange, &QPushButton::clicked, this, &CrawlSelectionDialog::onSelectInRangeOnly);
    connect(btnAll, &QPushButton::clicked, this, &CrawlSelectionDialog::onSelectAll);
    connect(btnNone, &QPushButton::clicked, this, &CrawlSelectionDialog::onDeselectAll);
    connect(m_listWidget, &QListWidget::itemChanged, this, &CrawlSelectionDialog::updateSelectionCount);
    connect(btnCancel, &QPushButton::clicked, this, &QDialog::reject);
    connect(m_btnConfirm, &QPushButton::clicked, this, &QDialog::accept);

    updateSelectionCount();
}

void CrawlSelectionDialog::onSelectAll()
{
    for (int i = 0; i < m_listWidget->count(); ++i) {
        m_listWidget->item(i)->setCheckState(Qt::Checked);
    }
    updateSelectionCount();
}

void CrawlSelectionDialog::onDeselectAll()
{
    for (int i = 0; i < m_listWidget->count(); ++i) {
        m_listWidget->item(i)->setCheckState(Qt::Unchecked);
    }
    updateSelectionCount();
}

void CrawlSelectionDialog::onSelectInRangeOnly()
{
    for (int i = 0; i < m_listWidget->count(); ++i) {
        auto *it = m_listWidget->item(i);
        bool inRange = it->data(Qt::UserRole + 1).toBool();
        it->setCheckState(inRange ? Qt::Checked : Qt::Unchecked);
    }
    updateSelectionCount();
}

void CrawlSelectionDialog::updateSelectionCount()
{
    int count = 0;
    for (int i = 0; i < m_listWidget->count(); ++i) {
        if (m_listWidget->item(i)->checkState() == Qt::Checked) count++;
    }
    if (m_labelCount) {
        m_labelCount->setText(QString("已勾选：<b>%1</b> / %2 篇").arg(count).arg(m_listWidget->count()));
    }
    if (m_btnConfirm) {
        m_btnConfirm->setEnabled(count > 0);
        m_btnConfirm->setText(QString("开始抓取选中的文章 (%1篇)").arg(count));
    }
}

QJsonArray CrawlSelectionDialog::selectedCandidates() const
{
    QJsonArray arr;
    for (int i = 0; i < m_listWidget->count(); ++i) {
        auto *it = m_listWidget->item(i);
        if (it->checkState() == Qt::Checked) {
            QByteArray raw = it->data(Qt::UserRole).toByteArray();
            auto doc = QJsonDocument::fromJson(raw);
            if (doc.isObject()) {
                arr.append(doc.object());
            }
        }
    }
    return arr;
}
