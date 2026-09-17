# OpsPilot — System Design & Architecture Document

OpsPilot is an enterprise-grade AI Operations Workflow Agent designed for automated IT and Fintech operations incident investigation, root-cause analysis, runbook retrieval (Agentic RAG), and controlled human-in-the-loop remediation.

---

## 1. System Overview & Core Objectives

Modern site-reliability and operations engineers spend up to 70% of incident resolution time performing repetitive diagnostic tasks: querying transaction ledgers, inspecting account states, searching for applicable operational runbooks, and submitting incident escalation tickets.

**OpsPilot** automates this end-to-end lifecycle with strict enterprise safety guarantees:
1. **Autonomous Diagnostic Investigation**: Orchestrated by a deterministic 14-node LangGraph state machine.
2. **Agentic RAG Engine**: Query decomposition, adaptive runbook retrieval, self-RAG relevance grading, and grounded multi-step reasoning traces.
3. **Deterministic Policy & Guardrails**: Hard rule engines evaluate risk levels before any mutation occurs; the LLM cannot directly trigger financial or infrastructure writes.
4. **Human-in-the-Loop (HITL)**: Medium and High-risk actions genuinely pause execution and require explicit cryptographic/operator approval.
5. **Full Observability & Auditability**: LangSmith traces every step, latency, and token; an append-only audit trail logs all operator and agent actions.

---

## 2. High-Level Architecture

```mermaid
graph TB
    subgraph ClientLayer ["Client Layer"]
        UI["OpsPilot SPA Dashboard<br/>(Vanilla JS / CSS Enterprise Theme)"]
        CLI["OpsPilot CLI / Automation Scripts"]
    end

    subgraph APILayer ["API & Ingestion Layer (FastAPI)"]
        Router["FastAPI Application Router"]
        AuthMiddleware["CORS & Request Validation Middleware"]
        TicketAPI["/tickets REST Endpoints"]
        AgentAPI["/agent/investigate & /state Endpoints"]
        ApprovalAPI["/approvals Approval Gate"]
        RAGAPI["/api/assistant/chat Agentic RAG"]
    end

    subgraph AgentCore ["Agentic Execution Engine (LangGraph)"]
        GraphEngine["14-Node StateGraph Workflow Engine"]
        Context["AgentState Context Memory"]
        PolicyEngine["Deterministic Policy Engine"]
    end

    subgraph RAGCore ["Agentic RAG Service"]
        Planner["Query Decomposition & Planning"]
        Retriever["Adaptive Runbook Retrieval"]
        Grader["Self-RAG Relevance Grader (0.0 - 1.0)"]
        Synthesizer["Grounded Synthesis & Citation Builder"]
    end

    subgraph ToolsLayer ["Tool Execution Layer (Controlled)"]
        subgraph ReadTools ["Read-Only Diagnostic Tools"]
            T_Cust["get_customer_details"]
            T_Bal["get_account_balance"]
            T_Txn["get_recent_transactions"]
            T_Fail["get_failed_transactions"]
            T_Hist["get_ticket_history"]
        end
        subgraph WriteTools ["Consequential Mutation Tools"]
            T_Inc["create_incident"]
            T_Ret["retry_payment"]
            T_Ref["initiate_refund"]
            T_Unl["unlock_account"]
        end
    end

    subgraph StorageLayer ["Data & Vector Storage"]
        SQL[(MySQL / SQLite ORM Layer)]
        VectorDB[(Pinecone / Mock Vector Store)]
        Runbooks[(Operational Runbooks Markdown)]
    end

    subgraph ObservabilityLayer ["Observability & Governance"]
        Audit["Immutable Audit Log"]
        LangSmith["LangChain Tracing v2 / LangSmith"]
    end

    UI --> Router
    CLI --> Router
    Router --> AuthMiddleware
    AuthMiddleware --> TicketAPI & AgentAPI & ApprovalAPI & RAGAPI

    AgentAPI --> GraphEngine
    RAGAPI --> RAGCore
    RAGCore --> VectorDB
    RAGCore --> Runbooks

    GraphEngine --> Context
    GraphEngine --> PolicyEngine
    GraphEngine --> ReadTools
    GraphEngine --> WriteTools
    GraphEngine --> RAGCore

    ReadTools --> SQL
    WriteTools --> SQL
    ApprovalAPI --> SQL

    GraphEngine --> Audit
    GraphEngine --> LangSmith
    Audit --> SQL
```

---

## 3. LangGraph Workflow & State Machine

The investigation lifecycle is modeled as a directed acyclic graph (DAG) with conditional branch routing and checkpoint interrupts for human approval.

```mermaid
stateDiagram-v2
    [*] --> ParseTicket : Ticket Submitted

    ParseTicket --> GatherEvidence : Extracted ticket metadata
    GatherEvidence --> AnalyzeEvidence : Diagnostic tools executed
    AnalyzeEvidence --> RetrieveRunbook : Evidence anomalies found
    RetrieveRunbook --> FormulateRecommendation : Runbook & historical matches
    FormulateRecommendation --> CheckPolicy : Proposed action & parameters

    state PolicyEvaluation <<choice>>
    CheckPolicy --> PolicyEvaluation

    PolicyEvaluation --> ExecuteAction : Risk = LOW (Auto-approved)
    PolicyEvaluation --> HumanApproval : Risk = MEDIUM or HIGH (Approval Required)

    state OperatorDecision <<choice>>
    HumanApproval --> OperatorDecision : Operator reviews recommendation

    OperatorDecision --> ExecuteAction : Operator APPROVED
    OperatorDecision --> ActionRejected : Operator REJECTED

    ExecuteAction --> UpdateTicket : Action completed & verified
    ActionRejected --> UpdateTicket : Ticket closed with rejection reason

    UpdateTicket --> NotifyOperator : UI badge & event emitted
    NotifyOperator --> LogAudit : Structured audit event written
    LogAudit --> [*] : Workflow Terminated
```

### Node Responsibilities:
| Node | Function | Output State Mutation |
|---|---|---|
| `parse_ticket` | Extracts customer ID, incident type, and symptoms from ticket description using Groq LLM with deterministic JSON parsing. | `customer_id`, `issue_type`, `symptoms` |
| `gather_evidence` | Invokes read-only diagnostic tools (`get_customer_details`, `get_failed_transactions`). | `evidence` dictionary |
| `analyze_evidence` | Correlates error codes (e.g. `ERR_GATEWAY_TIMEOUT`, `ERR_INSUFFICIENT_FUNDS`) and evaluates failure patterns. | `root_cause_hypothesis` |
| `retrieve_runbook` | Queries vector database with embedding of root cause hypothesis to retrieve relevant operational runbooks. | `runbook_text`, `runbook_id` |
| `formulate_recommendation` | Synthesizes evidence + runbook guidance into an action proposal (`create_incident`, `retry_payment`, `initiate_refund`, `unlock_account`). | `recommended_action`, `action_params` |
| `check_policy` | Deterministic policy engine assesses financial impact, blast radius, and assigns risk level (`LOW`, `MEDIUM`, `HIGH`). | `risk_level`, `requires_approval` |
| `human_approval` | **Interrupt Node**. Serializes state, registers `PendingApproval` record in database, and halts execution until operator decision. | `approval_status` |
| `execute_action` | Invokes the vetted write tool with Pydantic-validated parameters. | `execution_result` |
| `update_ticket` | Updates ticket status (`investigating` → `pending_approval` → `resolved`). | `ticket_status` |
| `notify_operator` | Emits UI notification payload and updates approval queue badges. | `notifications` |
| `log_audit` | Appends immutable record with actor attribution (`AGENT` or `OPERATOR`), timestamp, and full diff. | `audit_id` |

---

## 4. Agentic RAG Subsystem

OpsPilot incorporates an advanced **Agentic Retrieval-Augmented Generation (Self-RAG)** architecture to provide real-time runbook guidance and incident troubleshooting:

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator / Engineer
    participant API as /api/assistant/chat
    participant AgenticRAG as AgenticRAGService
    participant VectorStore as Pinecone / Runbook Index
    participant LLM as Groq Llama-3.3-70B

    User->>API: POST { message: "Why are payments failing with gateway timeout?", history }
    API->>AgenticRAG: chat(message, history, ticket_id)

    rect rgb(240, 245, 255)
        Note over AgenticRAG: Step 1: Query Decomposition & Intent Analysis
        AgenticRAG->>LLM: Classify intent, extract entities, decompose query
        LLM-->>AgenticRAG: Sub-queries: [payment gateway timeout, payment retry policy]
    end

    rect rgb(245, 255, 245)
        Note over AgenticRAG,VectorStore: Step 2: Adaptive Runbook Retrieval
        AgenticRAG->>VectorStore: Dense search (Top-K runbooks)
        VectorStore-->>AgenticRAG: Runbooks: [payment_gateway_timeout.md, failed_refund.md]
    end

    rect rgb(255, 250, 240)
        Note over AgenticRAG,LLM: Step 3: Self-RAG Relevance Grading
        loop For each retrieved chunk
            AgenticRAG->>LLM: Grade relevance (score 0.0 - 1.0, binary decision)
            LLM-->>AgenticRAG: Relevance scores (e.g. 0.95 relevant, 0.20 rejected)
        end
        AgenticRAG->>AgenticRAG: Filter chunks with score >= threshold (0.65)
    end

    rect rgb(250, 240, 255)
        Note over AgenticRAG,LLM: Step 4: Grounded Synthesis & Citation Assembly
        AgenticRAG->>LLM: Synthesize answer with structured bullet points and runbook citations
        LLM-->>AgenticRAG: Grounded response text
    end

    AgenticRAG-->>API: { answer, citations, steps: [Reasoning Trace] }
    API-->>User: JSON Response with Citations & Step Timeline
```

### Self-RAG Quality Checks:
- **Hallucination Mitigation**: Only runbook sections graded $\ge 0.65$ relevance are injected into the synthesis prompt.
- **Strict Evidence Grounding**: The LLM is instructed to cite explicit runbook filenames and sections (e.g., `payment_gateway_timeout.md`).
- **Explainability**: Every response includes an array of `steps` detailing decomposed sub-queries, retrieved files, relevance scores, and synthesis strategy.

---

## 5. Database Schema & Data Model

The data layer is built on SQLAlchemy ORM supporting both MySQL 8.0 (production) and SQLite (testing and local development).

```mermaid
erDiagram
    CUSTOMERS ||--o{ ACCOUNTS : owns
    CUSTOMERS ||--o{ SUPPORT_TICKETS : files
    ACCOUNTS ||--o{ TRANSACTIONS : records
    SUPPORT_TICKETS ||--o{ AGENT_RUNS : triggers
    SUPPORT_TICKETS ||--o{ PENDING_APPROVALS : requires
    SUPPORT_TICKETS ||--o{ AUDIT_LOGS : references

    CUSTOMERS {
        int id PK
        string full_name
        string email
        string tier
        datetime created_at
    }

    ACCOUNTS {
        int id PK
        int customer_id FK
        string account_number
        decimal balance
        string status
    }

    TRANSACTIONS {
        int id PK
        int account_id FK
        decimal amount
        string type
        string status
        string error_code
        datetime timestamp
    }

    SUPPORT_TICKETS {
        int id PK
        string ticket_number
        int customer_id FK
        string title
        text description
        string priority
        string status
        datetime created_at
    }

    AGENT_RUNS {
        int id PK
        string run_id UK
        int ticket_id FK
        string status
        text trace
        datetime started_at
        datetime completed_at
    }

    PENDING_APPROVALS {
        int id PK
        int ticket_id FK
        string run_id
        string action
        text parameters
        string risk_level
        string status
        datetime requested_at
        datetime decided_at
    }

    AUDIT_LOGS {
        int id PK
        int ticket_id FK
        string event
        string actor
        text details
        datetime timestamp
    }
```

---

## 6. Security, Safety & Human-in-the-Loop (HITL) Architecture

```mermaid
flowchart TD
    Req["LLM Proposes Action<br/>(e.g., initiate_refund, retry_payment)"] --> Validate["Pydantic Schema Validation"]
    Validate --> Policy{"Deterministic Policy Engine"}

    Policy -->|"Action == Read-Only"| AutoExec["Immediate Safe Execution"]
    Policy -->|"Action == initiate_refund & amount < $50"| LowRisk["Risk: LOW<br/>Auto-Executed & Logged"]
    Policy -->|"Action == initiate_refund & amount >= $50"| MedRisk["Risk: MEDIUM<br/>HITL Required"]
    Policy -->|"Action == unlock_account / create_incident"| HighRisk["Risk: HIGH<br/>HITL Required"]

    MedRisk --> Halt["Graph Interrupts / Halts"]
    HighRisk --> Halt
    Halt --> DB["Create PendingApproval Record in DB"]
    DB --> UI["Operator Dashboard Notification"]

    UI --> Decision{"Operator Action"}
    Decision -->|"Click APPROVE"| Exec["Resume State Machine & Execute Action"]
    Decision -->|"Click REJECT"| Abort["Cancel Action & Record Operator Feedback"]

    AutoExec --> Audit["Append-Only Audit Trail"]
    LowRisk --> Audit
    Exec --> Audit
    Abort --> Audit
```

### Safety Rules:
1. **Separation of Capabilities**: Read-only tools cannot alter state; write tools are strictly segregated and require validation schemas.
2. **Zero Direct LLM Execution**: The LLM outputs structured proposals; the backend execution engine verifies parameters before calling backend Python functions.
3. **Audit Immutability**: Every action, whether automatic or manual, generates an immutable audit record containing actor attribution (`AGENT`, `OPERATOR`, `SYSTEM`).
4. **Environment Isolation**: Production credentials and API keys are strictly loaded via `.env` and never leaked into client bundles or LLM contexts.

---

## 7. Technology Stack Summary

| Layer | Technologies Used | Rationale |
|---|---|---|
| **Backend Framework** | FastAPI, Python 3.11+, Uvicorn | Asynchronous I/O, auto-generated OpenAPI documentation, fast execution. |
| **Agent Orchestration** | LangGraph, LangChain Core | Explicit state graph management, checkpointing, and human-in-the-loop pauses. |
| **LLM Provider** | Groq (Llama-3.3-70B-Versatile) | Sub-second inference latency critical for interactive multi-step agent graphs. |
| **RAG & Vectors** | Pinecone, Sentence-Transformers | High-performance semantic retrieval over operational runbooks. |
| **Database & ORM** | SQLAlchemy 2.0, MySQL 8.0 / SQLite | Robust relational modeling, ACID guarantees for audit and transactions. |
| **Frontend** | Vanilla JavaScript (ES6+), HTML5, Custom CSS | Zero-dependency SPA, lightning-fast rendering, lightweight deployment. |
| **Observability** | LangSmith (LangChain Tracing v2) | Distributed step tracing, token counting, latency breakdowns, and run replays. |
| **Deployment & CI** | Docker, Docker Compose, GitHub Actions | Multi-stage container builds, automated testing (50+ unit tests), reproducible CI. |

---

## 8. Verification & Test Suite

The project includes an end-to-end automated test suite covering:
- **`tests/test_agent.py`**: Node execution, state transitions, fallback behavior, and approval routing.
- **`tests/test_rag.py`**: Embedding generation, vector similarity search, and mock fallbacks.
- **`tests/test_tools.py`**: Read tools, write tools, schema validation, and policy engine risk evaluations.

All 50 tests run isolated against in-memory SQLite and mock embeddings without requiring external cloud dependencies:
```bash
pytest tests -v --tb=short
```
