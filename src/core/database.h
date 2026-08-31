#pragma once
#include <QObject>
#include <QSqlDatabase>
#include "article.h"

// SQLite 持久化 - 存储文章、发布记录、博主配置
// Step2：文章表 + 发布历史；后续扩展用户/配置表
class Database : public QObject
{
    Q_OBJECT
public:
    explicit Database(QObject *parent = nullptr);
    static Database &instance();

    bool open(const QString &dbPath = {});
    bool isOpen() const;
    QString dbPath() const { return m_dbPath; }

    // 文章
    bool saveArticles(const QList<Article> &articles);
    QList<Article> loadArticles(const QString &bloggerId = {}, int limit = 100);
    Article loadArticle(const QString &id);
    bool clearArticles(const QString &bloggerId = {});

    // 发布记录
    struct PublishRecord {
        QString id;
        QString title;
        QString articleId;
        QString platform;
        QDateTime publishTime;
        bool success;
        QString message;
    };
    bool savePublishRecord(const PublishRecord &r);
    QList<PublishRecord> loadPublishRecords(int limit = 50);

private:
    bool createTables();
    QSqlDatabase m_db;
    QString m_dbPath;
};
