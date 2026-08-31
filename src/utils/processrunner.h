#pragma once
#include <QObject>
#include <QProcess>
#include <functional>

// 通用 QProcess 封装：负责启动 Python 脚本并处理 stdout/stderr/结束信号
// IwanMoney 的所有 Python 调用（爬取/润色/发布）均走此类
class ProcessRunner : public QObject
{
    Q_OBJECT
public:
    explicit ProcessRunner(QObject *parent = nullptr);
    ~ProcessRunner();

    // 同步/异步启动 python 脚本，返回是否成功启动
    bool start(const QString &pythonExe,
               const QStringList &args,
               const QString &workingDir = {});

    void kill();
    bool isRunning() const;

    QProcess *process() const { return m_process; }

signals:
    void finished(int exitCode, QProcess::ExitStatus status);
    void errorOccurred(const QString &msg);
    void stdoutReady(const QString &text);
    void stderrReady(const QString &text);

private:
    QProcess *m_process = nullptr;
};
