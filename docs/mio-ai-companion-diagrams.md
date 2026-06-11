# Mio AI Companion Diagrams

## 1. System Architecture

```mermaid
flowchart TB
    user["User"]
    web["Web Chat"]
    admin["Admin / Debug Console"]
    wechat["WeChat Webhook Simulator"]

    api["FastAPI API Layer"]
    graph["LangGraph Agent Workflow"]

    persona["Persona Layer"]
    emotion["Emotion Layer"]
    memory["Memory Layer"]
    rag["RAG Knowledge Layer"]
    tools["Tool Layer"]
    safety["Safety Guard"]
    trace["Trace Layer"]

    llm["LLM Provider Layer"]
    mockllm["Mock LLM"]
    realllm["OpenAI-compatible LLM"]

    db[("PostgreSQL")]
    vector[("pgvector")]
    media[("Media Storage")]

    user --> web
    user --> wechat
    admin --> api
    web --> api
    wechat --> api
    api --> graph

    graph --> emotion
    graph --> memory
    graph --> rag
    graph --> tools
    graph --> persona
    graph --> safety
    graph --> trace
    persona --> llm

    llm --> mockllm
    llm --> realllm

    memory --> db
    rag --> db
    rag --> vector
    tools --> media
    trace --> db
    safety --> db
```

## 2. Agent Conversation Workflow

```mermaid
flowchart TD
    start["User Message"] --> trace["Create trace_id"]
    trace --> saveUser["Save user message"]
    saveUser --> emotion["Emotion Classification"]
    emotion --> intent["Intent Router"]

    intent --> companion{"Intent"}
    companion -->|companion| memOnly["Retrieve long-term memory"]
    companion -->|knowledge_qa| ragOnly["Search learning KB"]
    companion -->|mixed| both["Retrieve memory + search KB"]
    companion -->|unsafe| safetyMode["Safety Support Mode"]

    memOnly --> prompt["Build Persona Prompt"]
    ragOnly --> prompt
    both --> prompt
    safetyMode --> safePrompt["Build Safety Prompt"]

    prompt --> llm["Generate Reply"]
    safePrompt --> llm
    llm --> safety["Safety Check"]
    safety --> sticker["Optional Sticker Selection"]
    sticker --> memoryExtract["Extract Candidate Memories"]
    memoryExtract --> saveAll["Save response, attachments, trace"]
    saveAll --> response["Return text + attachments"]
```

## 3. Core Module Map

```mermaid
flowchart LR
    subgraph Experience["Experience Layer"]
        chat["Chat"]
        personaSettings["Persona Settings"]
        kbPage["Knowledge Base"]
        memoryPage["Memory Center"]
        debugPage["Agent Debug"]
        skillPage["Skills / MCP"]
        learningReview["Learning Review"]
    end

    subgraph API["API Layer"]
        chatAPI["Chat API"]
        kbAPI["Knowledge API"]
        memoryAPI["Memory API"]
        personaAPI["Persona API"]
        traceAPI["Trace API"]
        webhookAPI["WeChat Webhook API"]
    end

    subgraph Agent["Agent Layer"]
        langgraph["LangGraph Workflow"]
        intent["Intent Router"]
        emotion["Emotion Classifier"]
        prompt["Prompt Builder"]
        guard["Safety Guard"]
    end

    subgraph Intelligence["Intelligence Layer"]
        persona["Persona Engine"]
        memory["Memory Service"]
        rag["RAG Service"]
        adaptive["Adaptive Learning"]
        tools["Tool Registry"]
        skills["Skill Registry"]
        mcp["MCP Tool Adapter"]
    end

    subgraph Storage["Storage Layer"]
        postgres[("PostgreSQL")]
        pgvector[("pgvector")]
        files[("Files / Stickers")]
    end

    Experience --> API
    API --> Agent
    Agent --> Intelligence
    Intelligence --> Storage
```

## 4. RAG And Memory Flow

```mermaid
flowchart TB
    upload["Upload Markdown / TXT"] --> classify["Choose KB Type"]
    classify --> companionKB["companion KB"]
    classify --> learningKB["learning KB"]

    companionKB --> chunk["Chunk Document"]
    learningKB --> chunk
    chunk --> embed["Generate Embedding"]
    embed --> storeChunks["Store Knowledge Chunks"]
    storeChunks --> vector[("pgvector")]

    msg["User Message"] --> intent["Intent Router"]
    intent -->|companion| memSearch["Search Memory"]
    intent -->|knowledge_qa| learningSearch["Search learning KB"]
    intent -->|mixed| mixedSearch["Search Memory + KB"]

    memSearch --> context["Context Pack"]
    learningSearch --> context
    mixedSearch --> context

    context --> persona["Persona Response Layer"]
    persona --> answer["Human-like RAG Answer"]

    answer --> extract["Extract Candidate Memory"]
    extract --> review{"Needs Review?"}
    review -->|yes| pending["Learning Review"]
    review -->|no| activeMemory["Active Memory"]
```

## 5. Adaptive Learning Loop

```mermaid
flowchart TD
    conversations["Recent Conversations"] --> reflection["Reflection Job"]
    traces["Agent Traces"] --> reflection
    emotions["Emotion History"] --> reflection
    ragQueries["RAG Queries"] --> reflection

    reflection --> candidates["Generate Candidate Updates"]
    candidates --> memoryCandidate["Candidate Memories"]
    candidates --> preferenceCandidate["Candidate Preferences"]
    candidates --> policyCandidate["Candidate Policies"]
    candidates --> skillCandidate["Skill / MCP Suggestions"]

    memoryCandidate --> review["Learning Review"]
    preferenceCandidate --> review
    policyCandidate --> review
    skillCandidate --> review

    review --> decision{"Approved?"}
    decision -->|yes| apply["Apply Change"]
    decision -->|no| reject["Reject / Archive"]

    apply --> memory["Memory"]
    apply --> state["CompanionState"]
    apply --> policy["Conversation Policy"]
    apply --> capabilities["Enabled Skills / MCP"]

    memory --> nextChat["Next Conversation"]
    state --> nextChat
    policy --> nextChat
    capabilities --> nextChat
```

## 6. Skill And MCP Extension Architecture

```mermaid
flowchart TB
    graph["LangGraph Workflow"] --> registry["Tool Registry"]

    registry --> builtin["Built-in Tools"]
    registry --> skills["Skill Registry"]
    registry --> mcpAdapter["MCP Tool Adapter"]

    builtin --> memoryTool["search_memory"]
    builtin --> kbTool["search_knowledge_base"]
    builtin --> stickerTool["select_sticker"]
    builtin --> reminderTool["create_reminder"]

    skills --> localStickerSkill["local-stickers Skill"]
    skills --> statusImageSkill["status-image Skill"]
    skills --> studyPlanSkill["study-plan Skill"]

    mcpAdapter --> mcpClient["MCP Client"]
    mcpClient --> fs["Filesystem MCP"]
    mcpClient --> notes["Notes MCP"]
    mcpClient --> calendar["Calendar MCP"]
    mcpClient --> github["GitHub MCP"]

    registry --> audit["Invocation Audit"]
    audit --> trace["Agent Trace"]
```

## 7. Deployment Modes

```mermaid
flowchart LR
    project["Mio AI Companion"]

    project --> personal["Personal Self-hosted Mode"]
    project --> demo["Public Demo Mode"]
    project --> hosted["Hosted Multi-user Mode"]

    personal --> p1["Single owner"]
    personal --> p2["Private memory"]
    personal --> p3["Private knowledge base"]
    personal --> p4["Local or personal server"]

    demo --> d1["Fake demo user"]
    demo --> d2["Seeded demo memory"]
    demo --> d3["Seeded learning KB"]
    demo --> d4["Restricted Skills / MCP"]
    demo --> d5["Resettable data"]

    hosted --> h1["Multi-user login"]
    hosted --> h2["Tenant isolation"]
    hosted --> h3["Quota and billing"]
    hosted --> h4["Content safety"]
    hosted --> h5["Admin console"]
```

## 8. Interview Demo Flow

```mermaid
sequenceDiagram
    participant I as Interviewer
    participant C as Chat
    participant A as Agent
    participant R as RAG
    participant M as Memory
    participant D as Debug Console
    participant L as Learning Review

    I->>C: 今天有点累，感觉转 AI 好难
    C->>A: Send message
    A->>M: Retrieve user memory
    A-->>C: Companion-style emotional support

    I->>C: LangGraph 和 LangChain 有什么区别？
    C->>A: Send question
    A->>R: Search learning KB
    R-->>A: Return relevant chunks
    A-->>C: Persona-grounded RAG answer

    I->>C: 我学 RAG 学崩了，retriever 到底是什么啊？
    C->>A: Send mixed message
    A->>M: Retrieve memory
    A->>R: Search RAG notes
    A-->>C: Comfort first, then explain retriever

    I->>D: Open trace
    D-->>I: emotion, intent, memory hits, RAG hits, tools, latency

    I->>L: Review candidate learning
    L-->>I: Approve new memory / policy
```

## 9. Avatar And Voice Architecture

```mermaid
flowchart TB
    user["User"]

    subgraph experience["Experience Layer"]
        chat["Web Chat"]
        call["Immersive Voice Call"]
        future["Future Desktop / Mobile"]
    end

    subgraph channels["Channel Layer"]
        textAdapter["Text Channel Adapter"]
        voiceAdapter["Voice Channel Adapter"]
    end

    subgraph voice["Voice Gateway"]
        session["Voice Session"]
        capture["Audio Upload / WebRTC"]
        vad["VAD"]
        asr["ASR Provider"]
        tts["TTS Provider"]
        interrupt["Interruption Controller"]
    end

    subgraph core["Mio Core Agent"]
        conversation["Conversation Service"]
        graph["LangGraph Workflow"]
        persona["Persona"]
        emotion["Emotion / Intent"]
        memory["Memory"]
        rag["RAG / Project Context"]
        safety["Safety"]
        trace["Agent Trace"]
    end

    subgraph presentation["Presentation Layer"]
        plan["Presentation Engine"]
        expression["Expression Mapper"]
        motion["Motion Mapper"]
        voiceStyle["Voice Style Mapper"]
    end

    subgraph runtime["Client Runtime"]
        controller["Avatar Controller"]
        renderer["Static / Live2D / VRM Renderer"]
        player["Audio Player"]
        lipsync["Audio Lip Sync"]
        subtitle["Subtitle Stream"]
        fallback["Static Avatar Fallback"]
    end

    user --> chat
    user --> call
    chat --> textAdapter
    call --> voiceAdapter
    future --> voiceAdapter

    textAdapter --> conversation
    voiceAdapter --> session
    session --> capture
    capture --> vad
    vad --> asr
    asr --> conversation

    conversation --> graph
    graph --> persona
    graph --> emotion
    graph --> memory
    graph --> rag
    graph --> safety
    graph --> trace

    graph --> plan
    plan --> expression
    plan --> motion
    plan --> voiceStyle

    voiceStyle --> tts
    tts --> player
    expression --> controller
    motion --> controller
    controller --> renderer
    player --> lipsync
    lipsync --> controller
    graph --> subtitle
    renderer -. load failure .-> fallback
    interrupt --> graph
    interrupt --> tts
```

## 10. Half-duplex Voice Turn

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web Client
    participant V as Voice Gateway
    participant A as ASR Provider
    participant C as Mio Core Agent
    participant P as Presentation Engine
    participant T as TTS Provider
    participant L as Avatar Runtime

    U->>W: Click record and speak
    W->>V: Upload audio
    V->>A: Transcribe
    A-->>V: Final transcript
    V-->>W: asr.final
    V->>C: Submit message to shared conversation
    C-->>W: agent.text.delta
    C->>P: Build presentation plan
    P-->>W: expression, motion, voice style
    C->>T: speech_text segments + request_id
    T-->>W: Audio chunks with sequence_id
    W->>W: Play chunks in sequence order
    W->>L: Play expression and motion
    W->>L: Drive lip sync from played audio
    C-->>W: response completed + trace_id
```

## 11. Realtime Voice State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Listening: start session
    Listening --> Transcribing: end of speech
    Transcribing --> Thinking: final transcript
    Thinking --> Speaking: first TTS audio
    Speaking --> Listening: barge-in, cancel TTS, save heard_text
    Speaking --> Idle: response completed
    Listening --> Reconnecting: WebRTC disconnected
    Speaking --> Reconnecting: WebRTC disconnected
    Reconnecting --> Listening: session restored
    Reconnecting --> Failed: timeout
    Listening --> Failed: ASR failure
    Thinking --> Failed: agent failure
    Speaking --> Failed: TTS failure
    Failed --> Idle: fall back to text or half-duplex
    Idle --> Ended: end session
    Listening --> Ended: end session
    Speaking --> Ended: end session
    Ended --> [*]
```
