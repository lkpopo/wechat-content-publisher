#pragma once
#include <QDialog>
#include <QListWidget>
#include <QPushButton>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QJsonObject>
#include <QJsonArray>

class CrawlSelectionDialog : public QDialog
{
    Q_OBJECT
public:
    explicit CrawlSelectionDialog(const QJsonArray &candidates, const QString &startDate, const QString &endDate, QWidget *parent = nullptr);

    QJsonArray selectedCandidates() const;

private slots:
    void onSelectAll();
    void onDeselectAll();
    void onSelectInRangeOnly();
    void updateSelectionCount();

private:
    void setupUi(const QJsonArray &candidates, const QString &startDate, const QString &endDate);

    QListWidget *m_listWidget = nullptr;
    QLabel *m_labelCount = nullptr;
    QPushButton *m_btnConfirm = nullptr;
};
