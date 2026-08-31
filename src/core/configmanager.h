#pragma once
#include <QObject>
#include <QJsonObject>
#include <QJsonDocument>
#include <QSettings>

// 本地配置管理：SQLite/JSON 二选一封装，目前先用 JSON 文件实现
// 后续可无缝切换为 QSqlDatabase(SQLite)
class ConfigManager : public QObject
{
    Q_OBJECT
public:
    explicit ConfigManager(QObject *parent = nullptr);
    static ConfigManager &instance();

    bool load();
    bool save();

    // 通用键值
    QVariant value(const QString &key, const QVariant &defaultValue = {}) const;
    void setValue(const QString &key, const QVariant &value);

    // 博主配置示例
    struct Blogger {
        QString id;
        QString name;
        QString platform; // wechat / weibo / xiaohongshu
        QString url;
    };
    QList<Blogger> bloggers() const;
    void addBlogger(const Blogger &b);
    void removeBlogger(const QString &id);

private:
    QString configFilePath() const;
    QJsonObject m_root;
};
