#include "processrunner.h"

ProcessRunner::ProcessRunner(QObject *parent) : QObject(parent)
{
    m_process = new QProcess(this);
    connect(m_process, &QProcess::readyReadStandardOutput, this, [this]{
        emit stdoutReady(QString::fromUtf8(m_process->readAllStandardOutput()));
    });
    connect(m_process, &QProcess::readyReadStandardError, this, [this]{
        emit stderrReady(QString::fromUtf8(m_process->readAllStandardError()));
    });
    connect(m_process, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &ProcessRunner::finished);
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError e){
        emit errorOccurred(m_process->errorString() + QString(" (%1)").arg(int(e)));
    });
}

ProcessRunner::~ProcessRunner()
{
    if (m_process && m_process->state() != QProcess::NotRunning) {
        m_process->kill();
        m_process->waitForFinished(2000);
    }
}

bool ProcessRunner::start(const QString &pythonExe, const QStringList &args, const QString &workingDir)
{
    if (m_process->state() != QProcess::NotRunning) return false;
    if (!workingDir.isEmpty()) m_process->setWorkingDirectory(workingDir);
    m_process->setProgram(pythonExe);
    m_process->setArguments(args);
    m_process->start();
    return m_process->waitForStarted(5000);
}

void ProcessRunner::kill()
{
    if (m_process->state() != QProcess::NotRunning) m_process->kill();
}

bool ProcessRunner::isRunning() const
{
    return m_process->state() != QProcess::NotRunning;
}
