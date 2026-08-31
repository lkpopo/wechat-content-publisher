#include <QApplication>
#include <QDir>
#include <QMessageBox>
#include "ui/mainwindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("IwanMoney");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("IwanTech");

    // 确保临时目录存在
    QDir tempDir(QApplication::applicationDirPath() + "/data/temp");
    if (!tempDir.exists()) {
        tempDir.mkpath(".");
    }
    QDir tempDir2(QDir::currentPath() + "/data/temp");
    if (!tempDir2.exists()) {
        tempDir2.mkpath(".");
    }

    MainWindow w;
    w.show();
    return app.exec();
}
