#include "themeManager.h"
#include <QApplication>
#include <QFile>
#include <QDebug>

ThemeManager::ThemeManager(QObject *parent) : QObject(parent) {}

ThemeManager &ThemeManager::instance()
{
    static ThemeManager s;
    return s;
}

QString ThemeManager::loadQss(const QString &resourcePath)
{
    QFile f(resourcePath);
    if (!f.exists()) {
        // fallback to file system (dev)
        QFile f2(QApplication::applicationDirPath() + resourcePath);
        if (f2.exists()) f.setFileName(f2.fileName());
        else {
            QFile f3("resources" + resourcePath.mid(1)); // :/styles/light.qss -> resources/styles/light.qss
            if (f3.exists()) f.setFileName(f3.fileName());
        }
    }
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qWarning() << "ThemeManager: cannot open" << resourcePath << f.errorString();
        return {};
    }
    return QString::fromUtf8(f.readAll());
}

bool ThemeManager::applyTheme(Theme theme)
{
    QString path = theme == Dark ? ":/styles/dark.qss" : ":/styles/light.qss";
    QString qss = loadQss(path);
    if (qss.isEmpty()) {
        // try file fallback
        qss = loadQss(QString(":/") + (theme==Dark?"styles/dark.qss":"styles/light.qss"));
    }
    if (qss.isEmpty()) return false;
    qApp->setStyleSheet(qss);
    m_theme = theme;
    emit themeChanged(theme);
    qDebug() << "Theme applied:" << themeName();
    return true;
}

bool ThemeManager::toggle()
{
    return applyTheme(m_theme == Light ? Dark : Light);
}
