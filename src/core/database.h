#pragma once
#include <QObject>
#include <QSqlDatabase>
#include "article.h"
#include "blogger.h"

// SQLite 持久化 - 存储文章、发布记录、博主配置
// Step2：文章表 + 发布历史 + 博主表
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

    // 博主
    bool saveBlogger(const Blogger &b);
    bool deleteBlogger(const QString &id);
    QList<Blogger> loadBloggers();
    Blogger loadBlogger(const QString &id);

private:
    bool createTables();
    QSqlDatabase m_db;
    QString m_dbPath;
};
