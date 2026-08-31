# IwanMoney - 自媒体内容搬运与发布客户端

> C++ Qt (主控/UI) + Python (爬虫/自动化) 多进程混合架构
> 工作流：选择博主 → 抓取文章 → AI自动润色(Grok) → 自动发布到今日头条

## Step1 已完成：基础骨架与双屏 UI + QProcess 链路打通

## 1. 项目结构

```
IwanMoney/
├── CMakeLists.txt               # CMake 构建 (Qt5.15.2 msvc2019_64)
├── src/
│   ├── main.cpp                 # 入口，确保 data/temp 存在
│   ├── ui/
│   │   ├── mainwindow.h/.cpp    # 主窗口 + QProcess 核心逻辑
│   │   └── mainwindow.ui        # Qt Designer 双屏布局
│   ├── core/
│   │   ├── configmanager.h/.cpp # 本地配置 (JSON，预留 SQLite)
│   │   └── (后续: datamodel.h)
│   └── utils/
│       ├── processrunner.h/.cpp # 通用 QProcess 封装
│       └── (后续: fileutils.h)
├── python/
│   ├── automation/
│   │   ├── ai_polish.py         # AI润色 Mock (已打通) + Playwright 预留
│   │   └── publisher.py         # 自动发布 骨架
│   ├── crawler/
│   │   └── crawler.py           # 爬虫接口骨架 (wechat/weibo/xhs) + Mock
│   ├── ai_polish.py             # 兼容入口，转发到 automation/ai_polish.py
│   └── requirements.txt
├── data/temp/                   # IPC 临时文件 (temp_in.txt / temp_out.txt / crawl_result.json)
├── config/                      # app_config.json
├── resources/                   # 图标、qss
└── docs/
```

### IPC 约定

| 方向 | 方式 | 细节 |
|------|------|------|
| C++ → Python | 命令行参数 | `python ai_polish.py temp_in.txt temp_out.txt` |
| C++ → Python | 临时文件 | `data/temp/temp_in.txt` (UTF-8) |
| Python → C++ | 临时文件 | `data/temp/temp_out.txt` |
| Python → C++ | stdout | 备用，C++ 在无文件时回退读取 stdout |
| 长文本 | 文件交换 | 避免命令行长度限制与编码问题 |

## 2. 主窗口 UI 设计

### Layout 层级
```
QMainWindow
 └─ centralwidget (QHBoxLayout, stretch 0:1)
     ├─ leftPanel (QVBoxLayout, 320-380px)
     │   ├─ comboPlatform (QComboBox) - 平台筛选 wechat/weibo/xiaohongshu
     │   ├─ listWidgetBloggers (QListWidget) - 博主列表，UserRole存 id/platform
     │   ├─ [QDateEdit Start] + "至" + [QDateEdit End]
     │   ├─ btnCrawl (开始爬取)
     │   └─ listWidgetArticles (QListWidget) - 文章列表，UserRole存正文
     └─ rightPanel (QVBoxLayout)
         ├─ lineEditTitle (标题)
         ├─ splitterEditor (QSplitter Horizontal)
         │   ├─ originalContainer → labelOriginal + textEditOriginal (QTextEdit)
         │   └─ polishedContainer → labelPolished + textEditPolished (QTextEdit)
         ├─ [btnClear] [btnSwap] [stretch] [btnPolish] [btnPublish]
         ├─ progressBar (busy, 仅运行时可见)
         └─ textEditLog (只读，深色日志)
     statusbar + menubar
```

### 关键 Widgets
- **博主列表**：`QListWidget` 每项 `setData(UserRole, id)` `UserRole+1, platform`，便于扩展
- **时间筛选**：`QDateEdit` calendarPopup=true，默认近7天
- **文章列表**：`QListWidget` alternatingRowColors，click 加载到 textEditOriginal
- **双屏对比**：`QSplitter` handleWidth=6，左右各一个 `QWidget` 包 `QLabel`+`QTextEdit`
- **底部按钮**：`btnCrawl` `btnPolish` `btnPublish` + `btnClear` `btnSwap`

## 3. QProcess 调用演示 (mainwindow.cpp:182-260)

```cpp
// 1. 保存左侧到 temp_in.txt
QFile inFile(m_tempInPath);
inFile.open(QIODevice::WriteOnly|QIODevice::Truncate|QIODevice::Text);
QTextStream ts(&inFile); ts.setCodec("UTF-8"); ts << ui->textEditOriginal->toPlainText();

// 2. 解析脚本路径（兼容开发/部署多候选）
QString scriptPath = resolvePythonScript("python/automation/ai_polish.py");

// 3. 启动 QProcess
m_polishProcess = new QProcess(this);
m_polishProcess->setProcessEnvironment(env); // PYTHONIOENCODING=utf-8
connect(m_polishProcess, &QProcess::finished, this, &MainWindow::onPolishFinished);
m_polishProcess->start(pythonExecutable(), {scriptPath, m_tempInPath, m_tempOutPath});

// 4. 结束回调读取 temp_out.txt 到右侧
void MainWindow::onPolishFinished(int exitCode, ...) {
    QFile outFile(m_tempOutPath);
    outFile.open(QIODevice::ReadOnly|QIODevice::Text);
    ui->textEditPolished->setPlainText(QTextStream(&outFile).readAll());
}
```

见 `src/ui/mainwindow.cpp:209-312` 完整实现，含错误处理、stdout 回退、进度条联动。

## 4. Python Mock

**ai_polish.py** (`python/automation/ai_polish.py:1`):
- `python ai_polish.py temp_in.txt temp_out.txt` 读取输入，开头加 `[已润色]`，写出输出
- 支持 `--stdin/--stdout` 与多编码回退
- 预留 `polish_with_playwright_stub()` 注释骨架

## 5. 构建与运行

### 环境
- Qt 5.15.2 msvc2019_64 (`C:/Qt/5.15.2/msvc2019_64/bin/qmake.exe`)
- CMake 3.16+, MSVC 2019
- Python 3.10+ (已验证 3.12.4)

### CMake 构建
```powershell
cmake -B build -S . -DCMAKE_PREFIX_PATH="C:/Qt/5.15.2/msvc2019_64"
cmake --build build --config Release
.\build\Release\IwanMoney.exe
# 或 Debug
cmake --build build --config Debug; .\build\Debug\IwanMoney.exe
```

### qmake 备选
```powershell
mkdir build-qmake; cd build-qmake
C:\Qt\5.15.2\msvc2019_64\bin\qmake.exe ..\IwanMoney.pro
nmake  # 或 jom / mingw32-make
```

### Python 链路自测（不启动 Qt）
```powershell
echo "这是一篇待润色的文章..." | python python/automation/ai_polish.py --stdin --stdout
python python/automation/ai_polish.py data/temp/temp_in.txt data/temp/temp_out.txt; cat data/temp/temp_out.txt
python python/crawler/crawler.py --blogger wechat_li_yongle --platform wechat --output data/temp/crawl_result.json; cat data/temp/crawl_result.json
```

## 6. 下一步 Step2

- [ ] 爬虫真实抓取：Playwright + BeautifulSoup 实现 WechatCrawler
- [ ] AI润色真实：Playwright 自动化 Grok，完成登录态复用、等待策略
- [ ] 发布真实：Playwright 操纵 mp.toutiao.com，处理草稿/封面/分类
- [ ] SQLite 持久化文章与发布记录
- [ ] 登录态管理与 Cookie 池
