#pragma once
#include <QString>

// 博主模型 - 对应 DB bloggers 表
struct Blogger {
    QString id;        // 唯一，如 wechat_li_yongle
    QString name;      // 显示名
    QString platform;  // wechat/weibo/xiaohongshu
    QString url;       // 主页链接（可选）
    bool verified = false;

    bool isValid() const { return !id.isEmpty() && !name.isEmpty() && !platform.isEmpty(); }
};
