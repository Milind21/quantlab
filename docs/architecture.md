# QuantLab architecture

**Agents propose, humans dispose.** A pipeline of specialized Gemini agents turns untrusted market
chatter into a *bounded, human-approved* risk action. The LLM never touches the order path.

```mermaid
flowchart TD
    W([Watchlist: tickers]):::io --> C

    subgraph SRC["Untrusted sources (allowlisted, rate-capped)"]
        direction LR
        RD[Reddit]:::src
        ST[StockTwits]:::src
        NR[News / RSS]:::src
        FX[Fixture · offline]:::src
    end
    SRC -->|raw posts| C

    C["🛰️ Collector<br/>normalize · treat as untrusted"]:::agent
    C -->|sanitized posts| A
    G{{"🛡️ Guardrails<br/>prompt-injection sanitizer ·<br/>strict-schema parse · token budget"}}:::guard
    C -.enforced by.- G

    A["🧠 Analyst · Gemini<br/>sentiment + confidence + themes"]:::agent
    MEM[("🗄️ Memory (SQLite)<br/>rolling sentiment baselines")]:::mem
    A <-->|Δ vs baseline = the signal| MEM
    A -->|sentiment + delta| CR

    CR["🔎 Critic · Gemini + heuristics<br/>organic vs coordinated / bot / echo"]:::agent
    CR -->|"⛔ veto / downgrade"| P
    CR -->|organic + material| P

    P["📝 Proposer<br/>tighten-only · bounded · evidence-linked · INERT"]:::agent
    P --> Q[["📥 Review queue<br/>(pending, inert)"]]:::io

    Q -->|"👤 human APPROVE<br/>(re-validated vs bounds)"| CFG[("✅ Versioned config<br/>+ audit · reversible")]:::good
    Q -->|"👤 reject / rollback"| NC([no change]):::io
    CFG -.->|reads params only| ENG["Deterministic trade engine<br/>(rules only — no LLM here)"]:::engine

    SURF["Surfaces: quantlab CLI · MCP server"]:::surf -.drives.- C

    classDef agent fill:#1f6feb,stroke:#0b3d91,color:#fff,rx:6,ry:6;
    classDef src fill:#30363d,stroke:#8b949e,color:#e6edf3;
    classDef guard fill:#8957e5,stroke:#5a32a3,color:#fff;
    classDef mem fill:#1a7f37,stroke:#0f5323,color:#fff;
    classDef good fill:#238636,stroke:#0f5323,color:#fff;
    classDef engine fill:#9e6a03,stroke:#5c3d00,color:#fff;
    classDef io fill:#161b22,stroke:#8b949e,color:#e6edf3;
    classDef surf fill:#0d1117,stroke:#58a6ff,color:#58a6ff;
```

**Key invariants (enforced in code, not by LLM goodwill):**
- The Proposer can only emit **tighten-only, bounded** `ParamProposal`s; loosening risk is rejected.
- A proposal is **inert** until a human approves; **approval is the only path** that changes config.
- The **Critic can veto** the Analyst — multi-agent disagreement filters manipulation.
- The trade engine reads config params but the **LLM is never in the order path**.
