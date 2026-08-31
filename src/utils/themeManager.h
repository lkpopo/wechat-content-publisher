#pragma once
#include <QObject>
#include <QString>

class ThemeManager : public QObject
{
    Q_OBJECT
public:
    enum Theme { Light, Dark };
    explicit ThemeManager(QObject *parent = nullptr);

    static ThemeManager &instance();
    Theme currentTheme() const { return m_theme; }
    bool isDark() const { return m_theme == Dark; }

    // 从资源或文件加载 QSS 并应用到 app
    bool applyTheme(Theme theme);
    bool toggle();

    QString themeName() const { return m_theme == Dark ? "dark" : "light"; }

signals:
    void themeChanged(Theme theme);

private:
    QString loadQss(const QString &resourcePath);
    Theme m_theme = Light;
};
