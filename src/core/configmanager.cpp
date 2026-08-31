#include "configmanager.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>

ConfigManager::ConfigManager(QObject *parent) : QObject(parent) {}

ConfigManager &ConfigManager::instance()
{
    static ConfigManager s;
    return s;
}

QString ConfigManager::configFilePath() const
{
    return QCoreApplication::applicationDirPath() + "/config/app_config.json";
}

bool ConfigManager::load()
{
    QFile f(configFilePath());
    if (!f.exists()) return true;
    if (!f.open(QIODevice::ReadOnly)) return false;
    auto doc = QJsonDocument::fromJson(f.readAll());
    if (doc.isObject()) m_root = doc.object();
    return true;
}

bool ConfigManager::save()
{
    QDir().mkpath(QFileInfo(configFilePath()).absolutePath());
    QFile f(configFilePath());
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    f.write(QJsonDocument(m_root).toJson(QJsonDocument::Indented));
    return true;
}

QVariant ConfigManager::value(const QString &key, const QVariant &defaultValue) const
{
    if (!m_root.contains(key)) return defaultValue;
    return m_root.value(key).toVariant();
}

void ConfigManager::setValue(const QString &key, const QVariant &value)
{
    m_root[key] = QJsonValue::fromVariant(value);
}

QList<ConfigManager::Blogger> ConfigManager::bloggers() const
{
    QList<Blogger> list;
    auto arr = m_root.value("bloggers").toArray();
    for (auto v : arr) {
        auto o = v.toObject();
        list.append({o["id"].toString(), o["name"].toString(), o["platform"].toString(), o["url"].toString()});
    }
    return list;
}

void ConfigManager::addBlogger(const Blogger &b)
{
    auto arr = m_root.value("bloggers").toArray();
    QJsonObject o; o["id"]=b.id; o["name"]=b.name; o["platform"]=b.platform; o["url"]=b.url;
    arr.append(o);
    m_root["bloggers"] = arr;
}

void ConfigManager::removeBlogger(const QString &id)
{
    auto arr = m_root.value("bloggers").toArray();
    QJsonArray next;
    for (auto v : arr) if (v.toObject()["id"].toString() != id) next.append(v);
    m_root["bloggers"] = next;
}
