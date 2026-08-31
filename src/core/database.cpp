#include "database.h"
#include <QCoreApplication>
#include <QDir>
#include <QSqlQuery>
#include <QSqlError>
#include <QDebug>
#include <QJsonDocument>

Database::Database(QObject *parent) : QObject(parent) {}

Database &Database::instance()
{
    static Database s;
    return s;
}

bool Database::open(const QString &dbPath)
{
    if (isOpen()) return true;
    QString path = dbPath;
    if (path.isEmpty()) {
        path = QCoreApplication::applicationDirPath() + "/data/app.db";
        // dev fallback
        if (!QFileInfo::exists(QFileInfo(path).absolutePath())) {
            QDir().mkpath(QFileInfo(path).absolutePath());
        }
        // also ensure data dir next to exe
        QDir().mkpath(QFileInfo(path).absolutePath());
    }
    m_dbPath = path;
    m_db = QSqlDatabase::addDatabase("QSQLITE", "IwanMoneyMain");
    m_db.setDatabaseName(path);
    if (!m_db.open()) {
        qWarning() << "Database open failed:" << m_db.lastError().text() << path;
        return false;
    }
    qDebug() << "Database opened:" << path;
    return createTables();
}

bool Database::isOpen() const { return m_db.isOpen(); }

bool Database::createTables()
{
    QSqlQuery q(m_db);
    // 文章表
    bool ok = q.exec(R"(
        CREATE TABLE IF NOT EXISTS articles(
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            platform TEXT,
            blogger_id TEXT,
            blogger_name TEXT,
            publish_time TEXT,
            url TEXT,
            cover TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    )");
    if (!ok) qWarning() << "create articles failed" << q.lastError();
    q.exec("CREATE INDEX IF NOT EXISTS idx_articles_blogger ON articles(blogger_id)");
    q.exec("CREATE INDEX IF NOT EXISTS idx_articles_platform ON articles(platform)");

    // 发布记录
    ok = q.exec(R"(
        CREATE TABLE IF NOT EXISTS publish_records(
            id TEXT PRIMARY KEY,
            title TEXT,
            article_id TEXT,
            platform TEXT,
            publish_time TEXT,
            success INTEGER,
            message TEXT
        )
    )");
    if (!ok) qWarning() << "create publish_records failed" << q.lastError();
    return true;
}

bool Database::saveArticles(const QList<Article> &articles)
{
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    m_db.transaction();
    for (auto &a : articles) {
        q.prepare("INSERT OR REPLACE INTO articles(id,title,content,platform,blogger_id,blogger_name,publish_time,url,cover) VALUES(?,?,?,?,?,?,?,?,?)");
        q.addBindValue(a.id);
        q.addBindValue(a.title);
        q.addBindValue(a.content);
        q.addBindValue(a.platform);
        q.addBindValue(a.bloggerId);
        q.addBindValue(a.bloggerName);
        q.addBindValue(a.publishTime.toString(Qt::ISODate));
        q.addBindValue(a.url);
        q.addBindValue(a.cover);
        if (!q.exec()) {
            qWarning() << "saveArticle failed" << q.lastError() << a.id;
        }
    }
    return m_db.commit();
}

QList<Article> Database::loadArticles(const QString &bloggerId, int limit)
{
    QList<Article> list;
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    if (bloggerId.isEmpty()) {
        q.prepare("SELECT id,title,content,platform,blogger_id,blogger_name,publish_time,url,cover FROM articles ORDER BY publish_time DESC LIMIT ?");
        q.addBindValue(limit);
    } else {
        q.prepare("SELECT id,title,content,platform,blogger_id,blogger_name,publish_time,url,cover FROM articles WHERE blogger_id=? ORDER BY publish_time DESC LIMIT ?");
        q.addBindValue(bloggerId);
        q.addBindValue(limit);
    }
    q.exec();
    while (q.next()) {
        Article a;
        a.id = q.value(0).toString();
        a.title = q.value(1).toString();
        a.content = q.value(2).toString();
        a.platform = q.value(3).toString();
        a.bloggerId = q.value(4).toString();
        a.bloggerName = q.value(5).toString();
        a.publishTime = QDateTime::fromString(q.value(6).toString(), Qt::ISODate);
        a.url = q.value(7).toString();
        a.cover = q.value(8).toString();
        list.append(a);
    }
    return list;
}

Article Database::loadArticle(const QString &id)
{
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    q.prepare("SELECT id,title,content,platform,blogger_id,blogger_name,publish_time,url,cover FROM articles WHERE id=?");
    q.addBindValue(id);
    q.exec();
    if (q.next()) {
        Article a;
        a.id = q.value(0).toString();
        a.title = q.value(1).toString();
        a.content = q.value(2).toString();
        a.platform = q.value(3).toString();
        a.bloggerId = q.value(4).toString();
        a.bloggerName = q.value(5).toString();
        a.publishTime = QDateTime::fromString(q.value(6).toString(), Qt::ISODate);
        a.url = q.value(7).toString();
        a.cover = q.value(8).toString();
        return a;
    }
    return {};
}

bool Database::clearArticles(const QString &bloggerId)
{
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    if (bloggerId.isEmpty()) return q.exec("DELETE FROM articles");
    q.prepare("DELETE FROM articles WHERE blogger_id=?");
    q.addBindValue(bloggerId);
    return q.exec();
}

bool Database::savePublishRecord(const PublishRecord &r)
{
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    q.prepare("INSERT OR REPLACE INTO publish_records(id,title,article_id,platform,publish_time,success,message) VALUES(?,?,?,?,?,?,?)");
    q.addBindValue(r.id);
    q.addBindValue(r.title);
    q.addBindValue(r.articleId);
    q.addBindValue(r.platform);
    q.addBindValue(r.publishTime.toString(Qt::ISODate));
    q.addBindValue(r.success?1:0);
    q.addBindValue(r.message);
    return q.exec();
}

QList<Database::PublishRecord> Database::loadPublishRecords(int limit)
{
    QList<PublishRecord> list;
    if (!isOpen()) open();
    QSqlQuery q(m_db);
    q.prepare("SELECT id,title,article_id,platform,publish_time,success,message FROM publish_records ORDER BY publish_time DESC LIMIT ?");
    q.addBindValue(limit);
    q.exec();
    while (q.next()) {
        PublishRecord r;
        r.id = q.value(0).toString();
        r.title = q.value(1).toString();
        r.articleId = q.value(2).toString();
        r.platform = q.value(3).toString();
        r.publishTime = QDateTime::fromString(q.value(4).toString(), Qt::ISODate);
        r.success = q.value(5).toInt()!=0;
        r.message = q.value(6).toString();
        list.append(r);
    }
    return list;
}
