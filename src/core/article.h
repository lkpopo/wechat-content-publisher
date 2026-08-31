#pragma once
#include <QString>
#include <QDateTime>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>

// 文章数据模型 - 兼容多平台，SQLite 行映射 + JSON 序列化
struct Article {
    QString id;           // 唯一ID: platform_blogger_idx / URL hash
    QString title;
    QString content;
    QString platform;     // wechat / weibo / xiaohongshu
    QString bloggerId;
    QString bloggerName;
    QDateTime publishTime;
    QString url;
    QString cover;
    QString rawJson;      // 额外字段存 JSON

    bool isValid() const { return !id.isEmpty() && !title.isEmpty(); }

    QJsonObject toJson() const {
        QJsonObject o;
        o["id"] = id;
        o["title"] = title;
        o["content"] = content;
        o["platform"] = platform;
        o["blogger_id"] = bloggerId;
        o["blogger_name"] = bloggerName;
        o["publish_time"] = publishTime.toString(Qt::ISODate);
        o["url"] = url;
        o["cover"] = cover;
        return o;
    }
    static Article fromJson(const QJsonObject &o) {
        Article a;
        a.id = o["id"].toString();
        a.title = o["title"].toString();
        a.content = o["content"].toString();
        a.platform = o["platform"].toString();
        a.bloggerId = o["blogger_id"].toString();
        a.bloggerName = o["blogger_name"].toString();
        a.publishTime = QDateTime::fromString(o["publish_time"].toString(), Qt::ISODate);
        a.url = o["url"].toString();
        a.cover = o["cover"].toString();
        return a;
    }
    // 用于 C++ <-> Python JSON 交换
    static QList<Article> listFromJsonArray(const QJsonArray &arr) {
        QList<Article> list;
        for (auto v : arr) list.append(fromJson(v.toObject()));
        return list;
    }
};
