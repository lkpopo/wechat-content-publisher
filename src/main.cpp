#include <QApplication>
#include <QDir>
#include <QFile>
#include <QSurfaceFormat>
#include "ui/mainwindow.h"
#include "utils/themeManager.h"
#include "core/database.h"

static void ensureDirs()
{
    for (auto p : {QApplication::applicationDirPath() + "/data/temp",
                   QApplication::applicationDirPath() + "/data",
                   QApplication::applicationDirPath() + "/config",
                   QDir::currentPath() + "/data/temp"}) {
        QDir().mkpath(p);
    }
}

int main(int argc, char *argv[])
{
    // 高分屏 + 字体渲染优化
    QApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
    // Windows 字体抗锯齿
    QCoreApplication::setAttribute(Qt::AA_UseStyleSheetPropagationInWidgetStyles, true);

    QApplication app(argc, argv);
    app.setApplicationName("IwanMoney");
    app.setApplicationVersion("2.0.0");
    app.setOrganizationName("IwanTech");

    // 全局字体：优先 HarmonyOS/思源/微软雅黑，解决默认 Inter 渲染模糊
    QFont font("Microsoft YaHei UI", 9);
    // 尝试更优字体
    for (auto name : {"HarmonyOS Sans SC", "Sarasa Gothic SC", "PingFang SC", "Microsoft YaHei UI"}) {
        QFont test(name);
        if (test.exactMatch() || QFontInfo(test).family() == name) { font.setFamily(name); break; }
    }
    font.setStyleStrategy(QFont::PreferAntialias);
    font.setHintingPreference(QFont::PreferFullHinting);
    app.setFont(font);

    ensureDirs();

    // 主题 - 优先尝试资源，其次文件
    ThemeManager::instance().applyTheme(ThemeManager::Light);
    // 若资源未打包，回退文件加载
    if (app.styleSheet().isEmpty()) {
        QFile f("resources/styles/light.qss");
        if (f.open(QIODevice::ReadOnly)) {
            app.setStyleSheet(QString::fromUtf8(f.readAll()));
        }
    }

    // 数据库
    Database::instance().open();

    MainWindow w;
    w.show();
    return app.exec();
}
