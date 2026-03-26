"""Seed the database with Pharmasyntez demo data."""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.base import Base
from app.models.document import Document, DocumentSource
from app.models.entity import DocumentEntity, Entity, EntityType, ExtractionMethod
from app.models.signal import Signal, SignalStatus, SignalType, TenantSignal
from app.models.tenant import Tenant
from app.models.user import User, UserRole

DATABASE_URL = os.environ.get(
    "SYNC_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://weaksignals:weaksignals@postgres:5432/weaksignals",
    ),
)

engine = create_engine(DATABASE_URL)


def seed():
    with Session(engine) as db:
        # Check if data already exists
        existing = db.query(Tenant).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # Add new enum values for document sources
        for src in ["pubmed", "clinicaltrials", "rss"]:
            try:
                db.execute(text(f"ALTER TYPE documentsource ADD VALUE IF NOT EXISTS '{src}'"))
                db.commit()
            except Exception:
                db.rollback()

        # Add cluster column to signals if not exists
        try:
            db.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS cluster VARCHAR(64)"))
            db.commit()
        except Exception:
            db.rollback()

        now = datetime.now(timezone.utc)

        # === TENANT: ГК Фармасинтез ===
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="ГК Фармасинтез",
            industry_verticals=[
                "Фармацевтика",
                "Биотехнологии",
                "Онкология",
                "Антиретровирусные препараты",
                "Антибиотики",
                "Противотуберкулёзные препараты",
                "Эндокринология",
            ],
            competitor_list={
                "Биокад": {"focus": "биопрепараты, онкология, рассеянный склероз", "threat": "high"},
                "Генериум": {"focus": "орфанные заболевания, 14 ВЗН", "threat": "high"},
                "Р-Фарм": {"focus": "госзаказ, импортозамещение, COVID", "threat": "medium"},
                "Промомед": {"focus": "инновационные препараты, IPO", "threat": "medium"},
                "Озон Фармацевтика": {"focus": "дженерики, масштаб", "threat": "medium"},
            },
            technology_watchlist=[
                "AI drug discovery",
                "CAR-T therapy",
                "mRNA vaccines",
                "Antibody-drug conjugates",
                "Biosimilars",
                "Digital twins clinical trials",
                "Self-driving laboratories",
                "CRISPR gene therapy",
                "GLP-1 receptor agonists",
                "Bispecific antibodies",
            ],
            signal_sensitivity=0.4,
            language_preferences=["ru", "en"],
        )
        db.add(tenant)

        # === USERS ===
        ceo_user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email="ceo@pharmasyntez.com",
            hashed_password=hash_password("demo123"),
            full_name="Викрам Пуния",
            role=UserRole.ceo,
            is_active=True,
        )
        analyst_user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email="analyst@pharmasyntez.com",
            hashed_password=hash_password("demo123"),
            full_name="Аналитик R&D",
            role=UserRole.analyst,
            is_active=True,
        )
        # Keep old demo user for backwards compatibility
        demo_user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email="ceo@techventures.com",
            hashed_password=hash_password("demo123"),
            full_name="Demo CEO",
            role=UserRole.ceo,
            is_active=True,
        )
        db.add_all([ceo_user, analyst_user, demo_user])

        # === INITIAL SIGNALS (pre-populated before first Gemini analysis) ===
        signals_data = [
            {
                "title": "Рост AI-платформ для ускорения поиска молекул-кандидатов",
                "description": "Крупные фармкомпании (Eli Lilly, Novartis) активно инвестируют в AI-платформы, сокращающие цикл drug discovery с 10 до 3-4 лет. Фармасинтезу критически важно оценить интеграцию AI в свой R&D-центр в Сколково.",
                "cluster": "ai_drug_discovery",
                "signal_type": SignalType.strong_signal,
                "novelty": 0.65,
                "momentum": 0.85,
                "composite": 0.78,
            },
            {
                "title": "Биокад начал III фазу КИ биоаналога окрелизумаба (BCD-281)",
                "description": "Конкурент Биокад запустил III фазу клинических исследований BCD-281 — биоаналога Окревус (Roche) для рассеянного склероза. Это подтверждает агрессивную стратегию Биокад в биоаналогах.",
                "cluster": "competitors_ru",
                "signal_type": SignalType.strong_signal,
                "novelty": 0.45,
                "momentum": 0.90,
                "composite": 0.72,
            },
            {
                "title": "Генериум получил регудостоверение на первый в мире биоаналог Наглазим",
                "description": "Генериум зарегистрировал первый в мире биоаналог галсульфазы для лечения орфанного мукополисахаридоза VI типа. Это демонстрирует лидерство Генериум в орфанном сегменте.",
                "cluster": "competitors_ru",
                "signal_type": SignalType.emerging_trend,
                "novelty": 0.70,
                "momentum": 0.60,
                "composite": 0.65,
            },
            {
                "title": "FDA расширяет фреймворк для AI-моделей в клинических исследованиях",
                "description": "FDA опубликовала проект руководства по оценке достоверности AI-моделей в клинической разработке с фокусом на 'context of use'. Это может ускорить регистрацию для компаний, использующих digital twins.",
                "cluster": "regulatory",
                "signal_type": SignalType.emerging_trend,
                "novelty": 0.75,
                "momentum": 0.70,
                "composite": 0.71,
            },
            {
                "title": "Партнёрство Фармасинтез-Hualan Bio: совместная разработка биопрепаратов",
                "description": "Стратегическое партнёрство с Hualan Bio открывает доступ к китайским технологиям производства моноклональных антител и вакцин. Совместная регистрация препаратов в ЕАЭС и за его пределами.",
                "cluster": "export_markets",
                "signal_type": SignalType.strong_signal,
                "novelty": 0.50,
                "momentum": 0.80,
                "composite": 0.68,
            },
            {
                "title": "Персонализированные мРНК-вакцины показывают 44% снижение рецидива меланомы",
                "description": "Комбинация мРНК-4157 с пембролизумабом (Moderna/Merck) показала 44% снижение риска рецидива меланомы в Phase 2b. Потенциально применимо к онкологическому портфелю Фармасинтеза.",
                "cluster": "oncology",
                "signal_type": SignalType.weak_signal,
                "novelty": 0.85,
                "momentum": 0.75,
                "composite": 0.80,
            },
            {
                "title": "Китайские biotech-компании увеличили долю глобальных лицензионных сделок до 32%",
                "description": "Доля китайских компаний в глобальных biotech-лицензионных сделках выросла с 21% до 32%. 5 из 10 крупнейших R&D-сделок 2025 года — из Китая. Стратегически важно для партнёрства с Hualan Bio.",
                "cluster": "export_markets",
                "signal_type": SignalType.emerging_trend,
                "novelty": 0.60,
                "momentum": 0.85,
                "composite": 0.73,
            },
            {
                "title": "Self-driving лаборатории получают крупное финансирование",
                "description": "Автономные лаборатории (robotic + AI) привлекают значительные инвестиции. Пока не доказали способность самостоятельно открывать валидированных кандидатов, но темпы развития ускоряются.",
                "cluster": "ai_drug_discovery",
                "signal_type": SignalType.weak_signal,
                "novelty": 0.80,
                "momentum": 0.65,
                "composite": 0.70,
            },
            {
                "title": "Патентные клифы биопрепаратов 2025-2028: окно возможностей для биоаналогов",
                "description": "В 2025-2028 истекают патенты на биопрепараты с суммарным объёмом продаж >$80 млрд (Humira, Keytruda, Stelara). Это создаёт значительные возможности для производителей биоаналогов.",
                "cluster": "biosimilars",
                "signal_type": SignalType.strong_signal,
                "novelty": 0.40,
                "momentum": 0.90,
                "composite": 0.70,
            },
            {
                "title": "Альтернативы животным моделям (NAMs): Charles River Labs меняет стратегию",
                "description": "Charles River Labs — крупнейшая CRO — переориентируется на NAMs (in vitro, in silico, organ-on-chip). Сигнал для всей индустрии: переход от животных моделей к human-relevant альтернативам.",
                "cluster": "regulatory",
                "signal_type": SignalType.weak_signal,
                "novelty": 0.75,
                "momentum": 0.55,
                "composite": 0.62,
            },
            {
                "title": "ADC (antibody-drug conjugates) — самый быстрорастущий сегмент онкологии",
                "description": "ADC-препараты (Enhertu, Padcev) демонстрируют впечатляющие результаты в солидных опухолях. Рынок ADC вырастет с $10 до $30+ млрд к 2030. Конъюгаты антител — перспективное направление для R&D Фармасинтеза.",
                "cluster": "oncology",
                "signal_type": SignalType.emerging_trend,
                "novelty": 0.55,
                "momentum": 0.90,
                "composite": 0.75,
            },
            {
                "title": "Промомед готовит IPO и расширяет портфель инновационных препаратов",
                "description": "Конкурент Промомед активно готовит IPO и наращивает инвестиции в собственные разработки. Усиление конкурента может повлиять на распределение госзаказа.",
                "cluster": "competitors_ru",
                "signal_type": SignalType.emerging_trend,
                "novelty": 0.50,
                "momentum": 0.70,
                "composite": 0.60,
            },
        ]

        signal_objects = []
        for i, sd in enumerate(signals_data):
            sig = Signal(
                id=uuid.uuid4(),
                title=sd["title"],
                description=sd["description"],
                cluster=sd["cluster"],
                signal_type=sd["signal_type"],
                novelty_score=sd["novelty"],
                momentum_score=sd["momentum"],
                composite_score=sd["composite"],
                confidence_level=sd.get("composite", 0.5),
                time_horizon="medium",
                impact_domains=[sd["cluster"]],
                first_detected=now - timedelta(days=i * 2),
                status=SignalStatus.active,
            )
            db.add(sig)
            signal_objects.append(sig)

        db.flush()

        # === TENANT-SIGNAL ASSOCIATIONS ===
        for sig in signal_objects:
            ts = TenantSignal(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                signal_id=sig.id,
                relevance_score=sig.composite_score * 0.9 + 0.1,
                industry_relevance=0.7 + (sig.novelty_score * 0.3),
                competitor_activity=0.5 if "competitors" in (sig.cluster or "") else 0.2,
                opportunity_score=sig.momentum_score * 0.8,
            )
            db.add(ts)

        db.commit()

        print("Database seeded successfully!")
        print(f"  - 1 tenant: ГК Фармасинтез")
        print(f"  - 3 users: ceo@pharmasyntez.com / demo123, analyst@pharmasyntez.com / demo123, ceo@techventures.com / demo123")
        print(f"  - {len(signal_objects)} initial signals")
        print(f"  - {len(signal_objects)} tenant-signal associations")


if __name__ == "__main__":
    seed()
