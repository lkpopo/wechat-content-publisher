import { useState, useEffect, useCallback } from 'react';
import {
  api,
  Article,
  ArticleListResponse,
  AIProvider,
  ProviderConfig,
  BatchCrawlResponse,
} from './api';

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    idle: '未处理',
    success: '发布成功',
  };
  return <span className={`status-badge status-${status}`}>{labels[status] || status}</span>;
}

function CrawlSection({ onSuccess }: { onSuccess: () => void }) {
  const [activeTab, setActiveTab] = useState<'single' | 'batch'>('single');
  const [singleUrl, setSingleUrl] = useState('');
  const [batchUrls, setBatchUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchCrawlResponse | null>(null);

  const handleSingleSubmit = async () => {
    if (!singleUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.fetchArticle(singleUrl.trim());
      setSingleUrl('');
      onSuccess();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchSubmit = async () => {
    const rawLines = batchUrls.split('\n');
    const urls = rawLines.map((l) => l.trim()).filter(Boolean);
    if (urls.length === 0) {
      setError('请输入至少一个有效的文章 URL');
      return;
    }

    setLoading(true);
    setError(null);
    setBatchResult(null);

    try {
      const result = await api.batchCrawlArticles(urls);
      setBatchResult(result);
      if (result.success_count > 0) {
        onSuccess();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="crawl-panel card">
      <div className="crawl-tabs">
        <button
          className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('single');
            setError(null);
          }}
        >
          单篇抓取
        </button>
        <button
          className={`tab-btn ${activeTab === 'batch' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('batch');
            setError(null);
          }}
        >
          批量抓取
        </button>
      </div>

      <div className="crawl-tab-content">
        {activeTab === 'single' ? (
          <div className="single-crawl-row">
            <input
              type="text"
              placeholder="输入微信公众号文章 URL (https://mp.weixin.qq.com/...)"
              value={singleUrl}
              onChange={(e) => setSingleUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSingleSubmit()}
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={handleSingleSubmit}
              disabled={loading || !singleUrl.trim()}
            >
              {loading ? '抓取中...' : '抓取文章'}
            </button>
          </div>
        ) : (
          <div className="batch-crawl-col">
            <div className="batch-hint">
              <span>支持多行输入，一行一个文章 URL。系统将自动过滤空行、首尾空格和重复 URL。</span>
            </div>
            <textarea
              className="batch-textarea"
              placeholder="https://mp.weixin.qq.com/s/...&#10;https://mp.weixin.qq.com/s/..."
              value={batchUrls}
              onChange={(e) => setBatchUrls(e.target.value)}
              rows={4}
              disabled={loading}
            />
            <div className="batch-actions">
              <button
                className="btn btn-primary"
                onClick={handleBatchSubmit}
                disabled={loading || !batchUrls.trim()}
              >
                {loading ? '正在批量抓取...' : '开始批量抓取'}
              </button>
              {batchUrls && (
                <button
                  className="btn btn-default btn-sm"
                  onClick={() => setBatchUrls('')}
                  disabled={loading}
                >
                  清空输入
                </button>
              )}
            </div>

            {batchResult && (
              <div className="batch-result-card">
                <div className="batch-result-summary">
                  <span className="summary-tag total">总共提交: {batchResult.total}</span>
                  <span className="summary-tag success">成功: {batchResult.success_count}</span>
                  <span className="summary-tag failed">失败: {batchResult.failed_count}</span>
                </div>
                <div className="batch-result-list">
                  {batchResult.results.map((item, idx) => (
                    <div key={idx} className={`batch-item ${item.status}`}>
                      <span className="item-idx">#{idx + 1}</span>
                      <span className={`status-badge status-${item.status === 'success' ? 'completed' : 'failed'}`}>
                        {item.status === 'success' ? '成功' : '失败'}
                      </span>
                      <span className="item-text" title={item.url}>
                        {item.title || item.url}
                      </span>
                      {item.error && <span className="item-error">{item.error}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

function ArticleList({
  onSelect,
  onRefresh,
}: {
  onSelect: (a: Article) => void;
  onRefresh: number;
}) {
  const [data, setData] = useState<ArticleListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.listArticles(0, 100);
      setData(result);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, onRefresh]);

  const copyUrl = (url: string, id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading && !data) return <div className="loading">加载文章列表中...</div>;

  return (
    <div className="article-list card">
      <div className="article-list-header">
        <h3>文章列表 ({data?.total || 0})</h3>
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          🔄 刷新列表
        </button>
      </div>

      {data?.items.length === 0 && (
        <div className="empty-state">暂无文章，请在上方输入 URL 抓取文章</div>
      )}

      {data?.items.map((article) => {
        const displayTitle =
          article.current_title || article.source_title || '未命名微信文章';

        const lastPublish =
          article.publish_records && article.publish_records.length > 0
            ? article.publish_records[article.publish_records.length - 1]
            : null;

        return (
          <div key={article.id} className="article-item">
            <div className="article-info">
              <div className="article-main-title" onClick={() => onSelect(article)}>
                {displayTitle}
                {article.current_title && (
                  <span className="title-length-tag">{displayTitle.length}字</span>
                )}
              </div>

              <div className="article-meta">
                {article.source_account && (
                  <span className="meta-tag account">来源: {article.source_account}</span>
                )}
                <span>抓取: <StatusBadge status={article.fetch_status} /></span>
                <span>AI改写: <StatusBadge status={article.ai_edit_status} /></span>
                {lastPublish ? (
                  <span>
                    今日头条:{' '}
                    <StatusBadge status={lastPublish.status} />
                  </span>
                ) : (
                  <span className="status-badge status-idle">头条未发布</span>
                )}
                <span className="meta-time">创建于: {article.created_at}</span>
              </div>

              <div className="article-url-row">
                <span className="url-text" title={article.source_url}>
                  🔗 {article.source_url}
                </span>
                <button
                  className="btn-link"
                  onClick={(e) => copyUrl(article.source_url, article.id, e)}
                >
                  {copiedId === article.id ? '已复制 ✓' : '复制链接'}
                </button>
              </div>

              {article.ai_edit_error && (
                <div className="error-message small">AI 改写提示: {article.ai_edit_error}</div>
              )}
            </div>

            <div className="actions">
              <button className="btn btn-primary" onClick={() => onSelect(article)}>
                编辑
              </button>
              <button
                className="btn btn-danger"
                onClick={async (e) => {
                  e.stopPropagation();
                  if (confirm(`确定要删除文章《${displayTitle}》吗？`)) {
                    await api.deleteArticle(article.id);
                    load();
                  }
                }}
              >
                删除
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}


function AIProgressBar({
  visible,
  progress,
  stepText,
  elapsed,
  isFinished,
  error,
}: {
  visible: boolean;
  progress: number;
  stepText: string;
  elapsed: number;
  isFinished?: boolean;
  error?: string | null;
}) {
  if (!visible) return null;

  return (
    <div className={`ai-status-banner card ${isFinished ? 'finished' : error ? 'failed' : 'active'}`}>
      <div className="ai-status-top">
        <div className="ai-status-info">
          <span className="ai-status-icon">
            {isFinished ? '✅' : error ? '❌' : '🤖'}
          </span>
          <div className="ai-status-text-wrap">
            <span className="ai-status-title">
              {isFinished ? 'AI 改写已就绪' : error ? 'AI 改写未完成' : 'AI 智能改写进行中...'}
            </span>
            <span className="ai-status-step">{stepText}</span>
          </div>
        </div>
        {!isFinished && !error && (
          <div className="ai-status-timer">
            <span className="timer-spinner"></span>
            <span>已耗时: <strong>{elapsed}</strong> 秒 (大模型处理约需10~25秒)</span>
          </div>
        )}
      </div>

      <div className="ai-progress-track">
        <div
          className={`ai-progress-bar ${isFinished ? 'finished' : error ? 'failed' : ''}`}
          style={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
        >
          <div className="ai-progress-glow"></div>
        </div>
      </div>

      <div className="ai-status-steps-row">
        <span className={`step-dot ${progress >= 15 ? 'done' : ''}`}>① 读取原文素材</span>
        <span className="step-arrow">→</span>
        <span className={`step-dot ${progress >= 45 ? 'done' : ''}`}>② 结构脉络重组</span>
        <span className="step-arrow">→</span>
        <span className={`step-dot ${progress >= 75 ? 'done' : ''}`}>③ ≤30字标题精炼</span>
        <span className="step-arrow">→</span>
        <span className={`step-dot ${progress >= 95 ? 'done' : ''}`}>④ 头条图文块生成</span>
      </div>
    </div>
  );
}

function ArticleDetail({
  articleId,
  onBack,
}: {
  articleId: string;
  onBack: () => void;
}) {
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<'edit' | 'preview'>('edit');
  const [isAiEditing, setIsAiEditing] = useState(false);
  const [aiProgress, setAiProgress] = useState(0);
  const [aiStepText, setAiStepText] = useState('');
  const [aiElapsedSeconds, setAiElapsedSeconds] = useState(0);
  const [aiFinished, setAiFinished] = useState(false);

  const loadArticle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const a = await api.getArticle(articleId);
      setArticle(a);
      setTitle(a.current_title || '');
      setContent(a.current_content || '');
      setHasUnsavedChanges(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [articleId]);

  useEffect(() => {
    loadArticle();
  }, [loadArticle]);

  useEffect(() => {
    if (article) {
      const unsaved =
        title !== (article.current_title || '') || content !== (article.current_content || '');
      setHasUnsavedChanges(unsaved);
    }
  }, [title, content, article]);

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
  };

  const handleAIEdit = async () => {
    if (!article) return;

    if (hasUnsavedChanges) {
      if (
        !confirm(
          '当前修改尚未保存，AI 编辑将基于已保存内容进行，未保存修改不会参与本次 AI 编辑。是否继续？'
        )
      ) {
        return;
      }
    }

    setError(null);
    setSuccessMsg(null);
    setIsAiEditing(true);
    setAiFinished(false);
    setAiProgress(8);
    setAiStepText('正在连接大模型并读取原文素材...');
    setAiElapsedSeconds(0);

    // 启动秒数递增与动态进度模拟
    let seconds = 0;
    const timer = setInterval(() => {
      seconds += 1;
      setAiElapsedSeconds(seconds);
      if (seconds <= 3) {
        setAiProgress(15 + seconds * 4);
        setAiStepText('📥 读取公众号原文素材与配图位置...');
      } else if (seconds <= 9) {
        setAiProgress(28 + (seconds - 3) * 6);
        setAiStepText('🧠 大模型深度分析脉络，重组文章结构...');
      } else if (seconds <= 16) {
        setAiProgress(65 + (seconds - 9) * 3);
        setAiStepText('✍️ 优化表达，提炼 ≤30 字符的高吸引力标题...');
      } else {
        setAiProgress(Math.min(94, 86 + (seconds - 16)));
        setAiStepText('🎨 格式化今日头条专用图文排版块...');
      }
    }, 1000);

    try {
      const updated = await api.aiEdit(article.id);
      clearInterval(timer);
      setArticle(updated);
      setTitle(updated.current_title || '');
      setContent(updated.current_content || '');
      setHasUnsavedChanges(false);

      if (updated.ai_edit_status === 'failed') {
        setIsAiEditing(false);
        setError(updated.ai_edit_error || 'AI 编辑失败');
      } else {
        setAiProgress(100);
        setAiFinished(true);
        const titleChars = updated.current_title ? updated.current_title.length : 0;
        setAiStepText(`🎉 AI 智能改写完成！新标题共 ${titleChars} 字（≤30字规范），正文排版已就绪`);
        setSuccessMsg(`AI 改写完成！标题已严格限制在 30 字符内（当前 ${titleChars} 字）`);

        // 4秒后自动收起完成状态栏
        setTimeout(() => {
          setIsAiEditing(false);
          setAiFinished(false);
        }, 4000);
      }
    } catch (e: any) {
      clearInterval(timer);
      setIsAiEditing(false);
      setError('AI 改写发生异常: ' + e.message);
    }
  };

  const handleSave = async () => {
    if (!article) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const trimmedTitle = title.length > 30 ? title.slice(0, 30) : title;
      const updated = await api.updateArticle(article.id, {
        current_title: trimmedTitle,
        current_content: content,
      });
      setArticle(updated);
      setTitle(updated.current_title || '');
      setHasUnsavedChanges(false);
      setSuccessMsg('修改已成功保存！');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!article) return;
    if (hasUnsavedChanges) {
      if (confirm('检测到有尚未保存的修改，建议先点击【保存】再发布。是否现在自动保存并发布？')) {
        await handleSave();
      } else {
        return;
      }
    }

    setPublishing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await api.publish(article.id);
      setSuccessMsg(result.message || '文章已成功发布到今日头条！');
      loadArticle();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPublishing(false);
    }
  };

  const handleClearHistory = async () => {
    if (!article) return;
    if (
      !confirm(
        '确定要清除该文章的所有发布历史记录吗？\n\n注意：清除历史不会删除文章正文和配图，仅清空历史日志。'
      )
    ) {
      return;
    }

    setClearingHistory(true);
    setError(null);
    try {
      const res = await api.clearPublishHistory(article.id);
      setSuccessMsg(res.message);
      loadArticle();
    } catch (e: any) {
      setError('清除发布历史失败: ' + e.message);
    } finally {
      setClearingHistory(false);
    }
  };

  if (loading) return <div className="loading">加载文章详情中...</div>;
  if (!article) return <div className="error-message">文章不存在</div>;

  const isAIProcessing = isAiEditing || article.ai_edit_status === 'processing';
  const getImageUrl = (imageId: string): string | null => {
    const idx = parseInt(imageId.replace('image_', ''));
    const img = article?.images.find((i) => i.image_index === idx);
    if (img?.local_path) {
      const filename = img.local_path.split(/[\\/]/).pop();
      return `/api/v1/images/${article.id}/${filename}`;
    }
    return null;
  };

  const renderOriginalContent = () => {
    const text = article.content_text || '';
    const lines = text.split('\n');
    return lines.map((line, i) => {
      const match = line.match(/^\[图(\d+)\]$/);
      if (match) {
        const idx = parseInt(match[1]);
        const imgUrl = getImageUrl(`image_${idx.toString().padStart(3, '0')}`);
        return (
          <div key={i} className="image-in-article">
            <span className="image-marker">[图{idx}]</span>
            {imgUrl && <img src={imgUrl} alt={`图${idx}`} className="article-image" />}
          </div>
        );
      }
      return <p key={i}>{line || '\u00A0'}</p>;
    });
  };

  const renderPreviewContent = () => {
    const text = content || '';
    const lines = text.split('\n\n');
    return (
      <div className="toutiao-mock-view">
        <h1 className="toutiao-title">{title || '未命名标题'}</h1>
        {/* <div className="toutiao-byline">
          <span className="toutiao-author">{article.source_account || '今日头条创作者'}</span>
          <span className="toutiao-time">刚刚 · 原创</span>
        </div> */}
        <div className="toutiao-body">
          {lines.map((line, i) => {
            const trimmed = line.trim();
            if (trimmed.startsWith('[image_')) {
              const imageId = trimmed.replace('[', '').replace(']', '');
              const imgUrl = getImageUrl(imageId);
              return (
                <div key={i} className="image-in-article toutiao-img-wrap">
                  {imgUrl ? (
                    <img src={imgUrl} alt={imageId} className="article-image" />
                  ) : (
                    <span className="image-marker">[{imageId}] 图片待上传</span>
                  )}
                </div>
              );
            }
            return <p key={i}>{line || '\u00A0'}</p>;
          })}
        </div>
      </div>
    );
  };

  const titleLen = title.length;

  return (
    <div className="article-detail-page">
      <div className="detail-top-nav card">
        <div className="nav-left">
          <button className="btn btn-default back-btn" onClick={onBack}>
            ← 返回文章列表
          </button>
          <div className="nav-title-group">
            <span className="nav-article-title" title={title || article.source_title || ''}>
              {title || article.source_title || '未命名文章'}
            </span>
            {hasUnsavedChanges && <span className="badge-warning">有未保存修改</span>}
          </div>
        </div>

        <div className="nav-actions">
          <button className="btn btn-primary" onClick={handleAIEdit} disabled={isAIProcessing}>
            {isAIProcessing ? 'AI 编辑中...' : '🤖 AI 智能改写'}
          </button>
          <button
            className="btn btn-default"
            onClick={handleSave}
            disabled={isAIProcessing || saving || !hasUnsavedChanges}
          >
            {saving ? '保存中...' : '💾 保存修改'}
          </button>
          <button
            className="btn btn-success"
            onClick={handlePublish}
            disabled={isAIProcessing || publishing}
          >
            {publishing ? '正在发布到今日头条...' : '🚀 发布到今日头条'}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {successMsg && <div className="success-message">{successMsg}</div>}

      {/* AI 智能改写高科技动态进度状态栏 */}
      <AIProgressBar
        visible={isAiEditing}
        progress={aiProgress}
        stepText={aiStepText}
        elapsed={aiElapsedSeconds}
        isFinished={aiFinished}
        error={error}
      />

      <div className="detail-layout">
        <div className="detail-section raw-section card">
          <div className="section-header raw-header">
            <div className="section-title">
              <span className="section-icon">📋</span>
              <h4>原始抓取文章 (只读)</h4>
            </div>
            <span className="readonly-badge">原始内容受保护</span>
          </div>

          <div className="raw-meta-bar">
            {article.source_account && <span>公众号: <strong>{article.source_account}</strong></span>}
            {article.author && <span>作者: {article.author}</span>}
            {article.publish_time && <span>发布时间: {article.publish_time}</span>}
            <span>配图数量: {article.images?.length || 0} 张</span>
          </div>

          <div className="original-article-scroll">
            {article.source_title && <h3 className="raw-source-title">{article.source_title}</h3>}
            {renderOriginalContent()}
          </div>
        </div>

        <div className="detail-section edit-section card">
          <div className="section-header edit-header">
            <div className="section-title">
              <span className="section-icon">✏️</span>
              <h4>头条发布工作台</h4>
            </div>
            <div className="mode-toggle">
              <button
                className={`toggle-btn ${activeRightTab === 'edit' ? 'active' : ''}`}
                onClick={() => setActiveRightTab('edit')}
              >
                ✏️ 内容编辑
              </button>
              <button
                className={`toggle-btn ${activeRightTab === 'preview' ? 'active' : ''}`}
                onClick={() => setActiveRightTab('preview')}
              >
                📱 头条发布预览
              </button>
            </div>
          </div>

          {isAIProcessing && (
            <div className="ai-processing-badge">
              <div className="loading-spinner small"></div>
              <span>AI 正在深度改写文章中，正在重组结构并提炼 ≤30 字符标题...</span>
            </div>
          )}

          {activeRightTab === 'edit' ? (
            <div className="edit-area">
              <div className="input-group">
                <div className="label-row">
                  <label>
                    文章标题 <span className="required">*</span>
                  </label>
                  <span
                    className={`char-counter ${titleLen > 30 ? 'overflow' : titleLen >= 25 ? 'warning' : ''}`}
                  >
                    {titleLen} / 30 字符
                  </span>
                </div>
                <input
                  className={`title-input ${titleLen > 30 ? 'has-error' : ''}`}
                  value={title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  placeholder="请输入文章标题 (必须 ≤ 30 字符)"
                  disabled={isAIProcessing}
                />
                {titleLen > 30 && (
                  <div className="field-hint error">
                    标题已超出 30 字符限制，保存或发布时将自动修剪至 30 字符！
                  </div>
                )}
              </div>

              <div className="input-group flex-fill">
                <div className="label-row">
                  <label>正文内容 (支持段落与 [image_xxx] 图片占位符)</label>
                  <span className="char-counter">{content.length} 字符</span>
                </div>
                <textarea
                  className="content-textarea"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="在此输入或编辑文章正文..."
                  disabled={isAIProcessing}
                />
              </div>
            </div>
          ) : (
            <div className="preview-area-container">
              <div className="preview-header-hint">
                <span>以下为发布至今日头条移动端/网页端的排版效果预览</span>
              </div>
              <div className="preview-scroll">{renderPreviewContent()}</div>
            </div>
          )}
        </div>
      </div>

      <div className="publish-history card">
        <div className="history-header">
          <div className="history-title">
            <h4>📜 发布历史 ({article.publish_records?.length || 0})</h4>
            <span className="history-subtitle">记录该文章向今日头条同步发布的历史日志</span>
          </div>
          {article.publish_records && article.publish_records.length > 0 && (
            <button
              className="btn btn-danger btn-sm"
              onClick={handleClearHistory}
              disabled={clearingHistory}
            >
              {clearingHistory ? '清除中...' : '🗑️ 清除发布历史'}
            </button>
          )}
        </div>

        {article.publish_records && article.publish_records.length > 0 ? (
          <div className="history-list">
            {article.publish_records.map((record) => (
              <div key={record.id} className="publish-record-item">
                <div className="record-main">
                  <span className={`status-badge status-${record.status}`}>
                    {record.status === 'success' ? '发布成功' : '发布失败'}
                  </span>
                  <span className="record-time">
                    {record.published_at || record.created_at}
                  </span>
                  <span className="record-title" title={record.title || ''}>
                    {record.title || '无标题'}
                  </span>
                </div>
                {record.error_message && (
                  <div className="record-error">{record.error_message}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-history">暂无发布历史记录</div>
        )}
      </div>
    </div>
  );
}

function SettingsPage({ onBack }: { onBack: () => void }) {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadProviders();
    loadConfig();
  }, []);

  const loadProviders = async () => {
    try {
      const res = await api.getProviders();
      setProviders(res.providers);
    } catch (e: any) {
      setMessage('加载失败: ' + e.message);
    }
  };

  const loadConfig = async () => {
    try {
      const res = await api.getProviderConfig();
      setConfig(res);
      setSelectedProvider(res.provider);
      setSelectedModel(res.model);
      setApiKey(res.api_key);
      setModels(res.models);
    } catch (e: any) {
      setMessage('加载配置失败: ' + e.message);
    }
  };

  const handleProviderChange = async (provider: string) => {
    setSelectedProvider(provider);
    setLoading(true);
    setMessage('');
    try {
      const res = await api.setProvider(provider);
      setConfig(res);
      setSelectedModel(res.model);
      setApiKey(res.api_key);
      setModels(res.models);
      if (res.has_models_api && res.api_key) {
        const modelRes = await api.getModels(provider);
        setModels(modelRes.models);
      }
    } catch (e: any) {
      setMessage('切换失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveApiKey = async () => {
    setLoading(true);
    setMessage('');
    try {
      await api.setApiKey(selectedProvider, apiKey);
      setMessage('API Key 已保存成功！');
    } catch (e: any) {
      setMessage('保存失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveModel = async () => {
    setLoading(true);
    setMessage('');
    try {
      await api.setModel(selectedProvider, selectedModel);
      setMessage('模型已保存成功！');
    } catch (e: any) {
      setMessage('保存失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchModels = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await api.getModels(selectedProvider);
      setModels(res.models);
      setMessage(`已获取 ${res.models.length} 个模型`);
    } catch (e: any) {
      setMessage('获取失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-container">
      <div className="settings-nav">
        <button className="btn btn-default" onClick={onBack}>
          ← 返回文章管理
        </button>
      </div>

      <div className="settings-panel card">
        <h3>AI 引擎配置</h3>
        <p className="settings-desc">
          配置用于微信公众号文章自动改写和标题提炼的大语言模型服务。
        </p>

        {message && <div className="error-message">{message}</div>}

        <div className="settings-section">
          <label>AI 提供商</label>
          <select
            value={selectedProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={loading}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} {p.api_configured ? '✓ (已配置)' : '(未配置)'}
              </option>
            ))}
          </select>
        </div>

        <div className="settings-section">
          <label>API Key</label>
          <div className="settings-row">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="输入提供商 API Key"
            />
            <button className="btn btn-primary" onClick={handleSaveApiKey} disabled={loading}>
              保存
            </button>
          </div>
        </div>

        <div className="settings-section">
          <label>选用模型</label>
          <div className="settings-row">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={loading}
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={handleSaveModel} disabled={loading}>
              保存
            </button>
            {config?.has_models_api && (
              <button className="btn btn-default" onClick={handleFetchModels} disabled={loading}>
                刷新模型列表
              </button>
            )}
          </div>
        </div>

        {config && (
          <div className="settings-info">
            <p>
              <strong>当前运行环境：</strong>
            </p>
            <p>服务商：{config.name}</p>
            <p>模型：{config.model}</p>
            <p>API 状态：{apiKey ? '✓ 已就绪' : '✗ 待配置'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<'list' | 'detail' | 'settings'>('list');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshList = () => setRefreshKey((k) => k + 1);

  const handleSelectArticle = (article: Article) => {
    setSelectedArticleId(article.id);
    setPage('detail');
  };

  const handleBackToList = () => {
    setPage('list');
    setSelectedArticleId(null);
    refreshList();
  };

  return (
    <div className="app-layout">
      <header className="global-header">
        <div className="header-left">
          <div className="brand-title" onClick={handleBackToList}>
            <span className="brand-icon">📰</span>
            <span className="brand-text">微信文章发布系统</span>
          </div>
          <nav className="global-nav">
            <button
              className={`nav-tab ${page === 'list' || page === 'detail' ? 'active' : ''}`}
              onClick={handleBackToList}
            >
              文章管理
            </button>
            <button
              className={`nav-tab ${page === 'settings' ? 'active' : ''}`}
              onClick={() => setPage('settings')}
            >
              AI 设置
            </button>
          </nav>
        </div>

        <div className="header-right">
          <span className="flow-badge">公众号 → AI改写(≤30字) → 今日头条发布</span>
          {page !== 'settings' && (
            <button className="btn btn-default btn-sm" onClick={() => setPage('settings')}>
              ⚙️ 设置
            </button>
          )}
        </div>
      </header>

      <main className="main-content">
        {page === 'list' && (
          <div className="list-page-container">
            <CrawlSection onSuccess={refreshList} />
            <ArticleList onSelect={handleSelectArticle} onRefresh={refreshKey} />
          </div>
        )}

        {page === 'detail' && selectedArticleId && (
          <ArticleDetail articleId={selectedArticleId} onBack={handleBackToList} />
        )}

        {page === 'settings' && <SettingsPage onBack={handleBackToList} />}
      </main>
    </div>
  );
}
