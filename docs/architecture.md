# QuantLab architecture

**Agents propose, humans dispose.** A pipeline of specialized Gemini agents turns untrusted market
chatter into a *bounded, human-approved* risk action. The LLM never touches the order path.

![QuantLab architecture](architecture.png)

<details><summary>Editable Mermaid source (rendered to <code>architecture.png</code>/<code>.svg</code> via kroki.io)</summary>

```mermaid
flowchart TD
    W([Watchlist]):::io --> C
    subgraph SRC["Untrusted sources"]
        direction LR
        RD[Reddit]:::src
        ST[StockTwits]:::src
        NR[News / RSS]:::src
        FX[Fixture]:::src
    end
    SRC -->|posts| C
    C["Collector"]:::agent
    G{{"Guardrails"}}:::guard
    C -.enforced by.- G
    C -->|sanitized| A
    A["Analyst · Gemini"]:::agent
    MEM[("Memory · SQLite")]:::mem
    A <-->|delta vs baseline| MEM
    A -->|sentiment| CR
    CR["Critic · Gemini"]:::agent
    CR -->|veto / organic| P
    P["Proposer"]:::agent
    P --> Q[["Review queue"]]:::io
    Q -->|human approve| CFG[("Config · versioned")]:::good
    Q -->|reject| NC([no change]):::io
    CFG -.->|params only| ENG["Trade engine · no LLM"]:::engine
    SURF["CLI · MCP server"]:::surf -.drives.- C

    classDef agent fill:#1f6feb,stroke:#0b3d91,color:#fff;
    classDef src fill:#30363d,stroke:#8b949e,color:#e6edf3;
    classDef guard fill:#8957e5,stroke:#5a32a3,color:#fff;
    classDef mem fill:#1a7f37,stroke:#0f5323,color:#fff;
    classDef good fill:#238636,stroke:#0f5323,color:#fff;
    classDef engine fill:#9e6a03,stroke:#5c3d00,color:#fff;
    classDef io fill:#161b22,stroke:#8b949e,color:#e6edf3;
    classDef surf fill:#0d1117,stroke:#58a6ff,color:#58a6ff;
```

To re-render after editing:
`curl -s https://kroki.io/mermaid/png --data-binary @architecture.mmd -o architecture.png`
(the ASCII-clean source lives in `architecture.mmd`).
</details>

**Legend — what each stage does:**
- **Collector** — pulls posts from allowlisted, rate-capped sources; treats every item as untrusted.
- **Guardrails** — prompt-injection sanitizer, strict-schema parsing, token budget (applied before any LLM call).
- **Analyst (Gemini)** — sentiment + confidence + themes; the signal is the **delta vs the ticker's rolling baseline** (from Memory).
- **Critic (Gemini + heuristics)** — organic vs coordinated / bot / echo; can **veto or downgrade** the analyst.
- **Proposer** — on a material, organic, bearish shift, emits a **tighten-only, bounded, evidence-linked** `ParamProposal` that is **inert**.
- **Review queue → human approve** — approval **re-validates against bounds**, writes a **versioned + audited** config change, and is **reversible**. This is the *only* path that changes config.
- **Trade engine** — reads config params only; the **LLM is never in the order path**.
- **Surfaces** — the `quantlab` CLI and an MCP server drive the same pipeline with identical guarantees.

**Key invariants (enforced in code, not by LLM goodwill):** tighten-only bounded proposals · inert
until human approval · critic can veto · LLM never in the order path.
