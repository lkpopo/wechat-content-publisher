import httpx
import json
import logging
from typing import Dict, Any
from app.config import settings
from app.provider_config import config_manager, PROVIDERS

logger = logging.getLogger(__name__)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "重新生成的文章标题",
        },
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["paragraph", "heading", "image"],
                    },
                    "text": {
                        "type": "string",
                        "description": "段落或标题文本",
                    },
                    "image_id": {
                        "type": "string",
                        "description": "图片ID，如 image_001",
                    },
                },
                "required": ["type"],
            },
        },
    },
    "required": ["title", "blocks"],
}

SYSTEM_PROMPT = """你是一个专业的中文内容编辑。请对微信公众号文章进行重新编辑，使其适合在今日头条发布。

## 标题核心要求【极度重要】
1. 重新生成一个吸引人的文章标题，**标题长度必须严格控制在 30 个字符以内（≤ 30 个字）**！
2. **绝对不允许生成超过 30 字符的标题**。
3. 保持标题自然、通顺、有吸引力，杜绝低俗标题党。
4. 如果原文标题过长，必须主动提炼核心事件并加以压缩精炼，确保总字数 ≤ 30。

## 正文编辑要求
1. 重新组织文章结构，调整段落顺序
2. 编辑和优化文字表达
3. 删除广告、推广、引流内容
4. 删除与核心主题无关的内容
5. 优化文章开头
6. 根据内容增加合理的小标题（使用 heading 类型）
7. 保留原文的重要事实、人物、时间、地点、数据
8. 不得虚构原文没有的信息
9. 不要逐句照抄原文
10. 不要简单进行机械同义词替换
11. 不要出现"微信公众号""本文转载""原文链接"等内容
12. 不输出分析过程

## 关于图片
原文中的 [图1]、[图2] 等标记表示图片位置。在输出中：
- 必须使用 {"type": "image", "image_id": "image_001"} 格式表示图片
- 不要将 [图1] 作为文本输出
- 图片编号必须与原文对应（图1 → image_001，图2 → image_002）
- 图片位置可随文章结构调整，但不能丢失

## 输出格式
严格按照以下 JSON 格式输出，不要包含任何其他文字：
{
  "title": "文章标题",
  "blocks": [
    {"type": "heading", "text": "小标题"},
    {"type": "paragraph", "text": "段落内容"},
    {"type": "image", "image_id": "image_001"},
    {"type": "paragraph", "text": "段落内容"}
  ]
}"""


async def generate_draft(content_text: str, max_retries: int = 3) -> Dict[str, Any]:
    provider_cfg = config_manager.get_provider_config()

    if not provider_cfg["api_key"]:
        raise ValueError(f"API key not configured for provider: {provider_cfg['name']}")

    prompt = f"## 原文内容\n{content_text}\n\n请按照系统提示中的要求重新编辑这篇文章。"
    logger.info(f"[AI] Provider: {provider_cfg['name']}, Model: {provider_cfg['model']}, Prompt length: {len(prompt)}")

    last_error = None
    for attempt in range(max_retries):
        try:
            if provider_cfg["provider"] == "opencode":
                result = await _call_opencode(provider_cfg, prompt)
            elif provider_cfg["provider"] == "deepseek":
                result = await _call_deepseek(provider_cfg, prompt)
            else:
                raise ValueError(f"Unknown provider: {provider_cfg['provider']}")
            return result
        except Exception as e:
            last_error = e
            logger.warning(f"[AI] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await __import__("asyncio").sleep(2 * (attempt + 1))

    raise RuntimeError(f"AI generation failed after {max_retries} retries: {last_error}")


async def _call_opencode(cfg: dict, prompt: str) -> Dict[str, Any]:
    request_body = {
        "model": cfg["model"],
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "article_output",
                "schema": OUTPUT_SCHEMA,
            }
        },
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{cfg['base_url']}/responses",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json=request_body,
        )
        response.raise_for_status()
        data = response.json()

    return _parse_opencode_response(data)


async def _call_deepseek(cfg: dict, prompt: str) -> Dict[str, Any]:
    request_body = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json=request_body,
        )
        response.raise_for_status()
        data = response.json()

    return _parse_deepseek_response(data)


def _parse_opencode_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if "output" in data and isinstance(data["output"], list):
        for item in data["output"]:
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return _parse_json_text(content.get("text", ""))
                    elif content.get("type") == "structured_output":
                        return content.get("json", {})

    if "content" in data and isinstance(data["content"], list):
        for item in data["content"]:
            if item.get("type") == "text":
                return _parse_json_text(item.get("text", ""))

    if "text" in data:
        return _parse_json_text(data["text"])

    raise ValueError(f"Unexpected API response format: {json.dumps(data, ensure_ascii=False)[:500]}")


def _parse_deepseek_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if "choices" in data and len(data["choices"]) > 0:
        message = data["choices"][0].get("message", {})
        content = message.get("content", "")
        return _parse_json_text(content)

    raise ValueError(f"Unexpected DeepSeek response format: {json.dumps(data, ensure_ascii=False)[:500]}")


def _parse_json_text(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI output as JSON: {e}\nText: {text[:500]}")

    if "title" not in result or "blocks" not in result:
        raise ValueError(f"AI output missing required fields: {list(result.keys())}")

    logger.info(f"[AI] Parsed: title={result.get('title', '(none)')[:30]}, blocks={len(result.get('blocks', []))}")
    return result


async def fetch_models(provider: str, api_key: str) -> list:
    if provider not in PROVIDERS:
        return []

    p = PROVIDERS[provider]

    if not p["has_models_api"]:
        return p["models"]

    try:
        base_url = p["base_url"]
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()

        models = []
        for item in data.get("data", []):
            models.append({
                "id": item.get("id", ""),
                "name": item.get("id", ""),
            })
        return models if models else p["models"]
    except Exception as e:
        logger.warning(f"[AI] Failed to fetch models for {provider}: {e}")
        return p["models"]
