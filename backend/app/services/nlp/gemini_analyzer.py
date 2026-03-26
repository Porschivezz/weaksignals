"""Gemini-powered signal analysis for weak signal detection.

Uses Google Gemini API for:
- Entity extraction from pharma/biotech documents
- Signal classification and scoring
- Weekly digest generation
"""

import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PHARMA_CLUSTERS = {
    "ai_drug_discovery": "AI в разработке лекарств",
    "oncology": "Онкология нового поколения",
    "biosimilars": "Биоаналоги и биосимиляры",
    "regulatory": "Регуляторика и GMP",
    "competitors_ru": "Конкуренты РФ",
    "export_markets": "Китай и экспортные рынки",
}

SYSTEM_PROMPT = """Ты — аналитик слабых сигналов для фармацевтической компании ГК «Фармасинтез» (Россия, топ-3 фармпроизводитель).

Контекст компании:
- Переход от дженериков к инновационным (оригинальным) препаратам
- R&D-центр в Сколково (запуск 2030)
- Партнёрство с Hualan Bio (Китай) по биотехнологиям
- В 2026 вывод 3 оригинальных препаратов: ХМЛ, антиспаечный, диабет II типа
- Патент США на новые соединения для ВИЧ
- Конкуренты: Биокад, Генериум, Р-Фарм, Промомед
- 6 заводов, 320+ препаратов, 6000 сотрудников

Кластеры мониторинга:
1. ai_drug_discovery — AI в разработке лекарств (AI-платформы, self-driving labs, digital twins)
2. oncology — Онкология нового поколения (CAR-T, ADC, мРНК-вакцины от рака, биспецифики)
3. biosimilars — Биоаналоги и биосимиляры (патентные клифы, моноклональные антитела)
4. regulatory — Регуляторика и GMP (FDA/EMA/Минздрав РФ, ускоренная регистрация, NAMs)
5. competitors_ru — Конкуренты РФ (Биокад, Генериум, Р-Фарм, Промомед — их КИ, партнёрства, M&A)
6. export_markets — Китай и экспортные рынки (ЕАЭС, лицензионные сделки, биотех Китая)

Ты отвечаешь СТРОГО в формате JSON."""


class GeminiAnalyzer:
    """Analyze documents and generate signals using Google Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _call_gemini(self, prompt: str) -> dict | None:
        """Call Gemini API and return parsed JSON response."""
        client = await self._get_client()
        url = f"{GEMINI_API_URL}?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }

        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            if not text:
                return None

            # Parse JSON, handle markdown fences
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API HTTP error: %s — %s", exc.response.status_code, exc.response.text[:500])
            return None
        except json.JSONDecodeError as exc:
            logger.error("Gemini response JSON parse error: %s", exc)
            return None
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            return None

    async def analyze_documents(self, documents: list[dict]) -> list[dict]:
        """Analyze a batch of documents and extract signals.

        Args:
            documents: List of dicts with 'title', 'abstract', 'source' fields.

        Returns:
            List of signal dicts with title, description, cluster, scores, entities.
        """
        if not documents:
            return []

        # Prepare document summaries for Gemini (batch up to 15 docs)
        doc_texts = []
        for i, doc in enumerate(documents[:15]):
            source = doc.get("source", "unknown")
            title = doc.get("title", "")
            abstract = (doc.get("abstract", "") or "")[:500]
            doc_texts.append(f"[{i+1}] ({source}) {title}\n{abstract}")

        docs_block = "\n\n".join(doc_texts)

        prompt = f"""Проанализируй следующие документы и извлеки слабые сигналы, релевантные для ГК «Фармасинтез».

ДОКУМЕНТЫ:
{docs_block}

Для каждого обнаруженного сигнала верни JSON-массив объектов:
{{
  "signals": [
    {{
      "title_ru": "Заголовок сигнала на русском",
      "title_en": "Signal title in English",
      "description_ru": "Краткое описание (2-3 предложения) почему это важно для Фармасинтеза",
      "cluster": "один из: ai_drug_discovery, oncology, biosimilars, regulatory, competitors_ru, export_markets",
      "novelty_score": 0.0-1.0,
      "momentum_score": 0.0-1.0,
      "relevance_to_pharmasyntez": 0.0-1.0,
      "signal_type": "weak_signal | emerging_trend | strong_signal",
      "entities": ["название_сущности1", "название_сущности2"],
      "source_doc_indices": [1, 3],
      "time_horizon": "short | medium | long",
      "impact_domains": ["oncology", "R&D", "regulatory"]
    }}
  ]
}}

Правила:
- Извлекай только сигналы, РЕАЛЬНО релевантные для Фармасинтеза
- novelty_score > 0.7 = реально новое, малоизвестное
- momentum_score = насколько быстро набирает обороты
- Если документы не содержат сигналов — верни пустой массив
- Не придумывай сигналы, которых нет в документах"""

        result = await self._call_gemini(prompt)
        if result is None:
            return []

        signals = result.get("signals", [])
        logger.info("Gemini extracted %d signals from %d documents", len(signals), len(documents))
        return signals

    async def generate_weekly_digest(
        self,
        signals: list[dict],
        period_start: str,
        period_end: str,
    ) -> dict | None:
        """Generate a weekly executive digest from top signals.

        Args:
            signals: List of signal dicts (title, description, scores, cluster).
            period_start: ISO date string.
            period_end: ISO date string.

        Returns:
            Digest dict with summary, key_insights, recommendations.
        """
        if not signals:
            return None

        signal_texts = []
        for i, s in enumerate(signals[:20]):
            title = s.get("title", s.get("title_ru", ""))
            desc = s.get("description", s.get("description_ru", ""))
            cluster = s.get("cluster", "")
            cluster_name = PHARMA_CLUSTERS.get(cluster, cluster)
            composite = s.get("composite_score", 0)
            signal_texts.append(
                f"[{i+1}] [{cluster_name}] {title} (score: {composite:.2f})\n{desc}"
            )

        signals_block = "\n\n".join(signal_texts)

        prompt = f"""Сгенерируй еженедельную аналитическую сводку для CEO ГК «Фармасинтез» за период {period_start} — {period_end}.

СИГНАЛЫ ЗА НЕДЕЛЮ:
{signals_block}

Верни JSON:
{{
  "executive_summary": "2-3 абзаца для CEO: что произошло за неделю, что важно, что требует внимания",
  "key_insights": [
    {{
      "insight": "Ключевой инсайт",
      "action_required": true/false,
      "priority": "high | medium | low"
    }}
  ],
  "recommendations": [
    "Конкретная рекомендация для CEO 1",
    "Конкретная рекомендация для CEO 2"
  ],
  "risk_alerts": ["Описание риска если есть"],
  "opportunities": ["Описание возможности если есть"]
}}

Пиши профессиональным бизнес-языком на русском. Фокус — на actionable insights для CEO."""

        result = await self._call_gemini(prompt)
        if result:
            logger.info("Generated weekly digest for %s — %s", period_start, period_end)
        return result

    async def enrich_signal(self, signal_title: str, signal_description: str, cluster: str) -> dict | None:
        """Enrich a signal with deeper analysis."""
        prompt = f"""Проведи глубокий анализ следующего слабого сигнала для ГК «Фармасинтез»:

Сигнал: {signal_title}
Описание: {signal_description}
Кластер: {PHARMA_CLUSTERS.get(cluster, cluster)}

Верни JSON:
{{
  "deep_analysis": "Подробный анализ (3-5 предложений): что это значит для Фармасинтеза",
  "competitive_implications": "Как это влияет на конкурентную позицию",
  "timeline": "Когда это может стать важным (конкретные сроки)",
  "related_technologies": ["технология1", "технология2"],
  "key_players": ["компания1", "компания2"],
  "recommended_actions": ["действие1", "действие2"]
}}"""

        return await self._call_gemini(prompt)
