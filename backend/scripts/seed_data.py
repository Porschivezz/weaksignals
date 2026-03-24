"""Seed the database with demo data for development/testing."""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.base import Base
from app.models.document import Document, DocumentSource
from app.models.entity import DocumentEntity, Entity, EntityType, ExtractionMethod
from app.models.signal import Signal, SignalStatus, SignalType, TenantSignal
from app.models.tenant import Tenant
from app.models.user import User, UserRole

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://weaksignals:weaksignals_dev@localhost:5432/weaksignals",
)

engine = create_engine(DATABASE_URL)


def seed():
    with Session(engine) as db:
        # Check if data already exists
        existing = db.query(Tenant).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        now = datetime.now(timezone.utc)

        # --- Tenants ---
        tenant1_id = uuid.uuid4()
        tenant2_id = uuid.uuid4()

        tenant1 = Tenant(
            id=tenant1_id,
            name="TechVentures Inc",
            industry_verticals=["artificial intelligence", "machine learning", "cloud computing"],
            competitor_list={
                "companies": ["DeepMind", "OpenAI", "Anthropic", "Cohere"],
                "institutions": ["Stanford University", "MIT", "Google Research"],
            },
            technology_watchlist=[
                "mixture of experts", "RLHF", "retrieval augmented generation",
                "model compression", "federated learning", "neuromorphic computing",
            ],
            signal_sensitivity=0.4,
            language_preferences=["en"],
        )
        tenant2 = Tenant(
            id=tenant2_id,
            name="BioPharm Corp",
            industry_verticals=["biotechnology", "pharmaceuticals", "AI drug discovery"],
            competitor_list={
                "companies": ["Recursion Pharma", "Insilico Medicine", "BenevolentAI"],
                "institutions": ["Harvard Medical School", "Johns Hopkins"],
            },
            technology_watchlist=[
                "protein folding", "generative chemistry", "clinical trial optimization",
                "digital twins", "multi-omics", "foundation models for biology",
            ],
            signal_sensitivity=0.5,
            language_preferences=["en"],
        )
        db.add_all([tenant1, tenant2])

        # --- Users ---
        user1 = User(
            id=uuid.uuid4(),
            tenant_id=tenant1_id,
            email="ceo@techventures.com",
            hashed_password=hash_password("demo123"),
            full_name="Alex Chen",
            role=UserRole.ceo,
            is_active=True,
        )
        user2 = User(
            id=uuid.uuid4(),
            tenant_id=tenant2_id,
            email="ceo@biopharm.com",
            hashed_password=hash_password("demo123"),
            full_name="Maria Ivanova",
            role=UserRole.ceo,
            is_active=True,
        )
        db.add_all([user1, user2])

        # --- Documents ---
        docs = []
        doc_data = [
            {
                "title": "Scaling Mixture-of-Experts Models Beyond Trillion Parameters",
                "abstract": "We present a novel approach to scaling Mixture-of-Experts (MoE) architectures to over one trillion parameters while maintaining training stability. Our method introduces dynamic expert routing with load balancing constraints that reduce expert collapse by 73%. Experiments on language modeling benchmarks show state-of-the-art performance with 4x less compute than dense equivalents.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.01234",
                "authors": [{"name": "Wei Zhang", "institution": "Tsinghua University", "orcid": None}],
            },
            {
                "title": "LoRA-XL: Parameter-Efficient Fine-Tuning at Scale",
                "abstract": "Low-Rank Adaptation (LoRA) has become the de facto method for parameter-efficient fine-tuning. We introduce LoRA-XL which extends the original formulation with adaptive rank selection and cross-layer weight sharing. On 15 downstream tasks, LoRA-XL matches full fine-tuning performance while updating only 0.1% of parameters.",
                "source": DocumentSource.semantic_scholar,
                "external_id": "S2:a1b2c3d4",
                "authors": [{"name": "Sarah Kim", "institution": "Stanford University", "orcid": None}],
            },
            {
                "title": "Retrieval-Augmented Generation with Dynamic Knowledge Graphs",
                "abstract": "We propose KG-RAG, a retrieval-augmented generation framework that dynamically constructs and queries knowledge graphs during inference. Unlike traditional RAG systems that retrieve flat documents, KG-RAG captures relational structure between entities, improving factual accuracy by 31% on knowledge-intensive QA benchmarks.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234567",
                "authors": [{"name": "James Wilson", "institution": "MIT", "orcid": None}],
            },
            {
                "title": "Liquid Neural Networks for Adaptive Real-Time Systems",
                "abstract": "Liquid Neural Networks (LNNs) represent a paradigm shift in continuous-time neural computation. We demonstrate that LNNs with only 19 neurons can control autonomous vehicles in complex environments, outperforming conventional networks with 100,000+ parameters. This work opens new possibilities for edge AI deployment.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.05678",
                "authors": [{"name": "Ramin Hasani", "institution": "MIT CSAIL", "orcid": None}],
            },
            {
                "title": "Constitutional AI: Training Harmless Assistants Through Self-Improvement",
                "abstract": "We present Constitutional AI (CAI), a method for training AI systems to be helpful, harmless, and honest without relying on human feedback for harmlessness. The approach uses a set of principles to guide AI self-critique and revision, producing models that are both more harmless and more capable than RLHF-trained counterparts.",
                "source": DocumentSource.semantic_scholar,
                "external_id": "S2:e5f6g7h8",
                "authors": [{"name": "Yuntao Bai", "institution": "Anthropic", "orcid": None}],
            },
            {
                "title": "Photonic Tensor Cores for Ultra-Fast Neural Network Inference",
                "abstract": "We demonstrate the first photonic tensor processing unit achieving 10 TOPS/W efficiency for neural network inference. Our silicon photonic chip performs matrix multiplications at the speed of light, offering 100x energy improvement over electronic GPUs for transformer inference workloads.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234568",
                "authors": [{"name": "Luca Nanni", "institution": "University of Oxford", "orcid": None}],
            },
            {
                "title": "AlphaFold3: Predicting Protein-Ligand Interactions with Atomic Accuracy",
                "abstract": "We extend protein structure prediction to protein-ligand complexes, achieving atomic-level accuracy in binding pose prediction. Our model combines diffusion-based generation with physical energy refinement, outperforming existing docking methods by a factor of 5 in success rate across diverse drug targets.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234569",
                "authors": [{"name": "John Jumper", "institution": "Google DeepMind", "orcid": None}],
            },
            {
                "title": "Neuromorphic Computing with Memristive Crossbar Arrays",
                "abstract": "We present a fully integrated neuromorphic chip using memristive crossbar arrays for in-memory computing. The chip achieves 1000x energy efficiency improvement for spiking neural network inference compared to von Neumann architectures. We demonstrate real-time pattern recognition at microwatt power levels.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.09012",
                "authors": [{"name": "Giacomo Indiveri", "institution": "ETH Zurich", "orcid": None}],
            },
            {
                "title": "Federated Learning with Differential Privacy at Enterprise Scale",
                "abstract": "We introduce FedDP-Enterprise, a production-ready federated learning framework that guarantees (epsilon, delta)-differential privacy with minimal utility loss. Deployed across 50 hospitals for medical imaging, our system achieves 97% of centralized accuracy while keeping all patient data on-premise.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234570",
                "authors": [{"name": "Brendan McMahan", "institution": "Google Research", "orcid": None}],
            },
            {
                "title": "State Space Models as Efficient Alternatives to Transformers",
                "abstract": "We show that structured state space models (S4, Mamba) achieve comparable performance to Transformers on language modeling while scaling linearly in sequence length. Our analysis reveals that the selective scan mechanism in Mamba effectively learns attention-like patterns with O(n) complexity.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.11234",
                "authors": [{"name": "Albert Gu", "institution": "Carnegie Mellon University", "orcid": None}],
            },
            {
                "title": "Multi-Modal Foundation Models for Drug Discovery",
                "abstract": "We present MolFormer-XL, a multi-modal foundation model trained on 1.1 billion molecular structures, protein sequences, and bioassay data. The model achieves state-of-the-art performance on 22 drug discovery benchmarks including virtual screening, ADMET prediction, and lead optimization.",
                "source": DocumentSource.semantic_scholar,
                "external_id": "S2:i9j0k1l2",
                "authors": [{"name": "Payel Das", "institution": "IBM Research", "orcid": None}],
            },
            {
                "title": "Quantum Error Correction with AI-Designed Codes",
                "abstract": "We use reinforcement learning to discover novel quantum error correction codes that outperform human-designed codes on realistic noise models. Our AI-discovered codes achieve a logical error rate 10x lower than surface codes at the same code distance, potentially accelerating the timeline to fault-tolerant quantum computing.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.13456",
                "authors": [{"name": "Shruti Puri", "institution": "Yale University", "orcid": None}],
            },
            {
                "title": "Agentic AI Systems: A Survey of Autonomous Problem Solving",
                "abstract": "We survey the emerging field of agentic AI systems that can autonomously decompose, plan, and execute complex tasks. We identify key architectural patterns including tool use, memory management, and self-reflection. Our benchmark AgentBench reveals that current systems solve only 23% of real-world software engineering tasks end-to-end.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234571",
                "authors": [{"name": "Shunyu Yao", "institution": "Princeton University", "orcid": None}],
            },
            {
                "title": "Direct Preference Optimization: Your Language Model is a Reward Model",
                "abstract": "We introduce Direct Preference Optimization (DPO), a stable and efficient algorithm for fine-tuning language models from human preferences. DPO eliminates the need for training a separate reward model, simplifying the RLHF pipeline while matching or exceeding PPO-based approaches on summarization and dialogue tasks.",
                "source": DocumentSource.arxiv,
                "external_id": "arxiv:2403.15678",
                "authors": [{"name": "Rafael Rafailov", "institution": "Stanford University", "orcid": None}],
            },
            {
                "title": "Graph Neural Networks for Climate Tipping Point Prediction",
                "abstract": "We develop a graph neural network model that predicts climate tipping points by learning interactions between Earth system components. Trained on paleoclimate data and coupled climate model outputs, our model identifies early warning signals of potential tipping cascades 50 years earlier than traditional statistical methods.",
                "source": DocumentSource.openalex,
                "external_id": "W4391234572",
                "authors": [{"name": "Niklas Boers", "institution": "TU Munich", "orcid": None}],
            },
        ]

        for i, d in enumerate(doc_data):
            doc = Document(
                id=uuid.uuid4(),
                title=d["title"],
                abstract=d["abstract"],
                source=d["source"],
                external_id=d["external_id"],
                authors=d["authors"],
                institutions=[a.get("institution") for a in d["authors"]],
                published_date=now - timedelta(days=30 - i * 2),
                processed=True,
            )
            docs.append(doc)
        db.add_all(docs)

        # --- Entities ---
        entity_data = [
            ("Mixture of Experts", EntityType.algorithm, ["MoE", "Sparse MoE"]),
            ("LoRA", EntityType.method, ["Low-Rank Adaptation", "LoRA-XL"]),
            ("Retrieval Augmented Generation", EntityType.method, ["RAG", "KG-RAG"]),
            ("Liquid Neural Networks", EntityType.algorithm, ["LNN", "Liquid Networks"]),
            ("Transformer", EntityType.algorithm, ["Self-Attention", "Multi-Head Attention"]),
            ("State Space Models", EntityType.algorithm, ["SSM", "Mamba", "S4"]),
            ("Photonic Computing", EntityType.technology, ["Photonic Tensor Core", "Silicon Photonics"]),
            ("Neuromorphic Computing", EntityType.technology, ["Memristive Crossbar", "Spiking Neural Networks"]),
            ("Federated Learning", EntityType.method, ["FL", "FedAvg", "FedDP"]),
            ("RLHF", EntityType.method, ["Reinforcement Learning from Human Feedback", "DPO", "Constitutional AI"]),
            ("Protein Folding", EntityType.method, ["AlphaFold", "Structure Prediction"]),
            ("Agentic AI", EntityType.technology, ["AI Agents", "Autonomous AI Systems"]),
            ("Quantum Error Correction", EntityType.technology, ["QEC", "Surface Codes"]),
            ("Foundation Models", EntityType.algorithm, ["Large Language Models", "LLM", "GPT"]),
        ]

        entities = []
        for name, etype, aliases in entity_data:
            entity = Entity(
                id=uuid.uuid4(),
                canonical_name=name,
                entity_type=etype,
                aliases=aliases,
                first_seen=now - timedelta(days=90),
            )
            entities.append(entity)
        db.add_all(entities)
        db.flush()

        # --- Document-Entity links ---
        links = [
            (0, 0), (0, 4), (1, 1), (1, 4), (2, 2), (2, 4),
            (3, 3), (4, 9), (5, 6), (6, 10), (7, 7),
            (8, 8), (9, 5), (9, 4), (10, 10), (10, 13),
            (11, 12), (12, 11), (13, 9), (14, 4),
        ]
        for doc_idx, ent_idx in links:
            de = DocumentEntity(
                id=uuid.uuid4(),
                document_id=docs[doc_idx].id,
                entity_id=entities[ent_idx].id,
                relevance_score=0.7 + (doc_idx % 3) * 0.1,
                extraction_method=ExtractionMethod.L1,
                raw_mention=entities[ent_idx].canonical_name,
            )
            db.add(de)

        # --- Signals ---
        signals_data = [
            {
                "title": "Liquid Neural Networks gaining momentum",
                "description": "A novel paradigm of continuous-time neural networks showing exponential growth in publications. Only 19 neurons needed to control autonomous vehicles — potential disruption for edge AI and embedded systems. Cross-domain migration detected from control theory to mainstream ML.",
                "signal_type": SignalType.weak_signal,
                "novelty_score": 0.87,
                "momentum_score": 0.72,
                "composite_score": 0.78,
                "confidence_level": 0.65,
                "time_horizon": "3y",
                "impact_domains": ["edge computing", "autonomous systems", "IoT"],
            },
            {
                "title": "Photonic computing approaching commercial viability",
                "description": "Silicon photonic tensor processing units achieving 100x energy efficiency over GPUs. Multiple research groups converging on similar architectures. Patent filings increased 340% in the last 6 months.",
                "signal_type": SignalType.weak_signal,
                "novelty_score": 0.75,
                "momentum_score": 0.68,
                "composite_score": 0.71,
                "confidence_level": 0.58,
                "time_horizon": "5y",
                "impact_domains": ["hardware", "data centers", "energy efficiency"],
            },
            {
                "title": "State Space Models challenging Transformer dominance",
                "description": "Mamba and S4 architectures achieving transformer-level performance with linear complexity. Growing community of researchers from 5 countries. Could reshape the entire foundation model landscape if scaling laws hold.",
                "signal_type": SignalType.emerging_trend,
                "novelty_score": 0.62,
                "momentum_score": 0.85,
                "composite_score": 0.73,
                "confidence_level": 0.72,
                "time_horizon": "1y",
                "impact_domains": ["NLP", "foundation models", "long-context applications"],
            },
            {
                "title": "Agentic AI systems reaching production readiness",
                "description": "Rapid convergence of tool-use, planning, and self-reflection patterns in AI systems. Enterprise adoption beginning with software engineering and customer support use cases.",
                "signal_type": SignalType.strong_signal,
                "novelty_score": 0.45,
                "momentum_score": 0.92,
                "composite_score": 0.82,
                "confidence_level": 0.85,
                "time_horizon": "1y",
                "impact_domains": ["software engineering", "customer support", "knowledge work"],
            },
            {
                "title": "DPO replacing RLHF as alignment standard",
                "description": "Direct Preference Optimization showing equivalent results to RLHF without reward model training. Adoption by major labs accelerating. Simplifies the alignment pipeline significantly.",
                "signal_type": SignalType.emerging_trend,
                "novelty_score": 0.55,
                "momentum_score": 0.78,
                "composite_score": 0.66,
                "confidence_level": 0.75,
                "time_horizon": "1y",
                "impact_domains": ["AI safety", "model training", "alignment"],
            },
            {
                "title": "AI-designed quantum error correction codes",
                "description": "Reinforcement learning discovering quantum error correction codes that outperform human-designed ones by 10x. Could accelerate fault-tolerant quantum computing timeline. Very early stage but high potential impact.",
                "signal_type": SignalType.weak_signal,
                "novelty_score": 0.92,
                "momentum_score": 0.45,
                "composite_score": 0.65,
                "confidence_level": 0.42,
                "time_horizon": "5y",
                "impact_domains": ["quantum computing", "cryptography", "materials science"],
            },
            {
                "title": "Neuromorphic-AI convergence accelerating",
                "description": "Memristive crossbar arrays enabling 1000x energy efficiency for spiking neural networks. Multiple chip designs reaching tape-out stage. Convergence with conventional deep learning methods being explored.",
                "signal_type": SignalType.weak_signal,
                "novelty_score": 0.70,
                "momentum_score": 0.55,
                "composite_score": 0.62,
                "confidence_level": 0.50,
                "time_horizon": "3y",
                "impact_domains": ["hardware", "edge AI", "brain-computer interfaces"],
            },
            {
                "title": "Multi-modal foundation models transforming drug discovery",
                "description": "Models trained on molecular structures, protein sequences, and bioassay data achieving SOTA on 22 drug discovery benchmarks. Pharmaceutical industry rapidly adopting these tools for lead optimization.",
                "signal_type": SignalType.emerging_trend,
                "novelty_score": 0.58,
                "momentum_score": 0.82,
                "composite_score": 0.70,
                "confidence_level": 0.78,
                "time_horizon": "1y",
                "impact_domains": ["drug discovery", "pharmaceuticals", "biotechnology"],
            },
        ]

        signal_objects = []
        for i, sd in enumerate(signals_data):
            sig = Signal(
                id=uuid.uuid4(),
                title=sd["title"],
                description=sd["description"],
                signal_type=sd["signal_type"],
                novelty_score=sd["novelty_score"],
                momentum_score=sd["momentum_score"],
                composite_score=sd["composite_score"],
                confidence_level=sd["confidence_level"],
                time_horizon=sd["time_horizon"],
                impact_domains=sd["impact_domains"],
                evidence_ids=[docs[i % len(docs)].id, docs[(i + 3) % len(docs)].id],
                first_detected=now - timedelta(days=20 - i * 2),
                status=SignalStatus.active,
            )
            signal_objects.append(sig)
        db.add_all(signal_objects)
        db.flush()

        # --- Tenant-Signal associations ---
        # TechVentures: interested in AI/ML signals
        tech_relevance = [0.92, 0.78, 0.95, 0.88, 0.82, 0.45, 0.65, 0.35]
        for i, sig in enumerate(signal_objects):
            ts = TenantSignal(
                id=uuid.uuid4(),
                tenant_id=tenant1_id,
                signal_id=sig.id,
                relevance_score=tech_relevance[i],
                industry_relevance=tech_relevance[i] * 0.9,
                competitor_activity=0.3 + (i % 4) * 0.15,
                opportunity_score=tech_relevance[i] * 0.85,
                is_dismissed=False,
            )
            db.add(ts)

        # BioPharm: interested in biotech/drug discovery signals
        bio_relevance = [0.25, 0.30, 0.40, 0.55, 0.20, 0.60, 0.35, 0.95]
        for i, sig in enumerate(signal_objects):
            ts = TenantSignal(
                id=uuid.uuid4(),
                tenant_id=tenant2_id,
                signal_id=sig.id,
                relevance_score=bio_relevance[i],
                industry_relevance=bio_relevance[i] * 0.9,
                competitor_activity=0.2 + (i % 3) * 0.1,
                opportunity_score=bio_relevance[i] * 0.8,
                is_dismissed=False,
            )
            db.add(ts)

        db.commit()
        print("Database seeded successfully!")
        print(f"  - 2 tenants: TechVentures Inc, BioPharm Corp")
        print(f"  - 2 users: ceo@techventures.com / demo123, ceo@biopharm.com / demo123")
        print(f"  - {len(docs)} documents")
        print(f"  - {len(entities)} entities")
        print(f"  - {len(signal_objects)} signals")
        print(f"  - {len(signal_objects) * 2} tenant-signal associations")


if __name__ == "__main__":
    seed()
