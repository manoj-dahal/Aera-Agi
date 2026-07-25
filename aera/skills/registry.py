"""The AERA skill catalogue.

A *skill* is a named unit of capability, finer-grained than an agent: one agent
usually provides many skills. The catalogue is what lets AERA answer "can I
actually do this?" before promising an answer.

Every skill declares:

* the **agent** that executes it,
* the **backend** it needs (a model, a library, an OS facility),
* an **availability** state resolved at runtime.

Availability is deliberately first-class. A skill that needs OCR is listed even
when Tesseract is absent - it reports ``needs_backend`` rather than vanishing or
pretending to work. That self-knowledge is what stops the router handing work to
something that will fabricate a result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SkillCategory(str, Enum):
    """Top-level grouping, mirroring the specified taxonomy."""

    CORE = "core"
    CODING = "coding"
    SECURITY = "security"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    WEB = "web"
    WORKSPACE = "workspace"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    AI = "ai"
    LEARNING = "learning"
    DEVICE = "device"
    CREATIVE = "creative"
    PRODUCTIVITY = "productivity"
    SYSTEM = "system"


class Availability(str, Enum):
    """Whether a skill can run right now."""

    #: Fully operational with what is installed.
    AVAILABLE = "available"
    #: Implemented, but a backend is missing (model, library, permission).
    NEEDS_BACKEND = "needs_backend"
    #: Disabled by configuration or policy.
    DISABLED = "disabled"
    #: Catalogued for completeness; no implementation yet.
    PLANNED = "planned"


class Backend(str, Enum):
    """External capability a skill depends on."""

    NONE = "none"                 # works with the built-in reasoner
    LLM = "llm"                   # any text model (built-in counts)
    VISION_MODEL = "vision_model"
    OCR_ENGINE = "ocr_engine"
    STT_ENGINE = "stt_engine"
    TTS_ENGINE = "tts_engine"
    IMAGE_MODEL = "image_model"
    VIDEO_TOOLS = "video_tools"
    NETWORK = "network"
    TERMINAL = "terminal"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    GIT = "git"
    DOC_PARSER = "doc_parser"     # PDF/DOCX/XLSX parsing
    DEVICE_LINK = "device_link"   # paired phone


@dataclass(frozen=True, slots=True)
class Skill:
    """One catalogued capability."""

    id: str
    name: str
    category: SkillCategory
    description: str
    #: Agent that executes this skill.
    agent: str
    #: What must be present for it to run.
    backend: Backend = Backend.LLM
    #: Runs continuously in the background rather than on request.
    background: bool = False
    #: Free-text matching hints for skill resolution.
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "agent": self.agent,
            "backend": self.backend.value,
            "background": self.background,
        }


def _s(
    id: str,
    name: str,
    category: SkillCategory,
    agent: str,
    description: str,
    backend: Backend = Backend.LLM,
    *,
    background: bool = False,
    keywords: tuple[str, ...] = (),
) -> Skill:
    return Skill(
        id=id,
        name=name,
        category=category,
        description=description,
        agent=agent,
        backend=backend,
        background=background,
        keywords=keywords,
    )


C = SkillCategory
B = Backend

#: The full catalogue.
SKILLS: tuple[Skill, ...] = (
    # ---------------------------------------------------------------- core
    _s("nlu", "Natural Language Understanding", C.CORE, "core",
       "Parses intent and meaning from free-text requests.", B.NONE,
       background=True, keywords=("understand", "parse", "meaning")),
    _s("context_awareness", "Context Awareness", C.CORE, "core",
       "Tracks the active project, conversation and open files.", B.NONE,
       background=True),
    _s("multi_step_reasoning", "Multi-Step Reasoning", C.CORE, "reasoning",
       "Works through problems in explicit stages.", B.LLM,
       keywords=("why", "explain", "analyse", "reason")),
    _s("decision_making", "Decision Making", C.CORE, "reasoning",
       "Weighs options and commits to a recommendation.", B.LLM,
       keywords=("decide", "choose", "recommend", "should i")),
    _s("task_planning", "Task Planning", C.CORE, "planning",
       "Turns a goal into an ordered, dependency-aware plan.", B.LLM,
       keywords=("plan", "steps", "roadmap")),
    _s("goal_decomposition", "Goal Decomposition", C.CORE, "planning",
       "Breaks a large objective into workable pieces.", B.LLM,
       keywords=("break down", "decompose", "milestones")),
    _s("conversation_management", "Conversation Management", C.CORE, "conversation",
       "Maintains dialogue state and continuity across sessions.", B.LLM),
    _s("memory_recall", "Memory Recall", C.CORE, "memory",
       "Hybrid semantic and keyword retrieval over the graph.", B.NONE,
       background=True, keywords=("remember", "recall", "what did")),
    _s("memory_writing", "Memory Writing", C.CORE, "memory",
       "Stores new knowledge and links it into the graph.", B.NONE,
       background=True),
    _s("context_switching", "Context Switching", C.CORE, "core",
       "Moves cleanly between projects and conversations.", B.NONE,
       background=True),
    _s("intent_recognition", "Intent Recognition", C.CORE, "core",
       "Classifies a request into a routable capability.", B.NONE,
       background=True),

    # -------------------------------------------------------------- coding
    _s("code_generation", "Code Generation", C.CODING, "coding",
       "Writes code across sixteen supported languages.", B.LLM,
       keywords=("write", "implement", "create function", "code")),
    _s("code_completion", "Code Completion", C.CODING, "coding",
       "Completes partial implementations in context.", B.LLM),
    _s("debugging", "Debugging", C.CODING, "debug",
       "Diagnoses stack traces and proposes a minimal fix.", B.LLM,
       keywords=("debug", "traceback", "error", "crash")),
    _s("refactoring", "Refactoring", C.CODING, "coding",
       "Restructures code without changing behaviour.", B.LLM,
       keywords=("refactor", "clean up", "restructure")),
    _s("code_review", "Code Review", C.CODING, "code_review",
       "Reviews for correctness, security, performance and style.", B.LLM,
       keywords=("review", "critique")),
    _s("documentation_generation", "Documentation Generation", C.CODING, "writing",
       "Produces docstrings, READMEs and reference docs.", B.LLM,
       keywords=("document", "docstring", "readme")),
    _s("unit_test_generation", "Unit Test Generation", C.CODING, "coding",
       "Writes tests covering the described behaviour.", B.LLM,
       keywords=("test", "pytest", "unit test")),
    _s("api_development", "API Development", C.CODING, "coding",
       "Designs and implements HTTP and RPC interfaces.", B.LLM,
       keywords=("api", "endpoint", "rest")),
    _s("database_development", "Database Development", C.CODING, "coding",
       "Schema design, queries and migrations.", B.LLM,
       keywords=("database", "sql", "schema", "migration")),
    _s("frontend_development", "Frontend Development", C.CODING, "coding",
       "UI implementation in the major frameworks.", B.LLM,
       keywords=("frontend", "react", "css", "ui code")),
    _s("backend_development", "Backend Development", C.CODING, "coding",
       "Server-side services and business logic.", B.LLM,
       keywords=("backend", "server", "service")),
    _s("fullstack_development", "Full-Stack Development", C.CODING, "coding",
       "End-to-end feature work across both tiers.", B.LLM,
       keywords=("full stack", "fullstack")),
    _s("devops_assistance", "DevOps Assistance", C.CODING, "coding",
       "CI/CD pipelines, build and release guidance.", B.LLM,
       keywords=("ci", "cd", "pipeline", "deploy")),
    _s("git_operations", "Git Operations", C.CODING, "git",
       "Repository analysis, commits, branches and history.", B.GIT,
       keywords=("git", "commit", "branch", "merge")),
    _s("terminal_automation", "Terminal Automation", C.CODING, "terminal",
       "Runs allowlisted shell commands.", B.TERMINAL,
       keywords=("run", "shell", "command", "terminal")),
    _s("docker_management", "Docker Management", C.CODING, "terminal",
       "Container inspection through the terminal.", B.DOCKER,
       keywords=("docker", "container", "image")),
    _s("kubernetes_support", "Kubernetes Support", C.CODING, "coding",
       "Manifest authoring and cluster guidance.", B.KUBERNETES,
       keywords=("kubernetes", "k8s", "helm", "pod")),

    # ------------------------------------------------------------ security
    _s("ethical_hacking", "Ethical Hacking Assistance", C.SECURITY, "ethical_hacking",
       "Authorised defensive assessment of systems you own.", B.LLM,
       keywords=("pentest", "ethical hacking", "authorised test")),
    _s("vulnerability_analysis", "Vulnerability Analysis", C.SECURITY, "ethical_hacking",
       "Identifies and ranks weaknesses by severity.", B.LLM,
       keywords=("vulnerability", "cve", "weakness")),
    _s("network_security", "Network Security Assessment", C.SECURITY, "network",
       "Local reachability and exposure checks.", B.NONE,
       keywords=("network security", "port", "exposure")),
    _s("web_security", "Web Security Testing", C.SECURITY, "ethical_hacking",
       "Reviews web application security posture.", B.LLM,
       keywords=("xss", "csrf", "injection", "web security")),
    _s("api_security", "API Security Review", C.SECURITY, "ethical_hacking",
       "Auth, rate limiting and exposure review for APIs.", B.LLM,
       keywords=("api security", "auth review")),
    _s("static_analysis", "Static Code Security Analysis", C.SECURITY, "code_review",
       "Finds insecure patterns in source without running it.", B.LLM,
       keywords=("static analysis", "sast", "insecure code")),
    _s("malware_detection", "Malware Detection", C.SECURITY, "security",
       "Heuristic review of suspicious files and behaviour.", B.LLM,
       keywords=("malware", "virus", "suspicious")),
    _s("threat_detection", "Threat Detection", C.SECURITY, "monitoring",
       "Watches for anomalous system behaviour.", B.NONE, background=True),
    _s("log_analysis", "Log Analysis", C.SECURITY, "document",
       "Reads logs and surfaces the significant events.", B.LLM,
       keywords=("log", "logs", "audit trail")),
    _s("permission_analysis", "Permission Analysis", C.SECURITY, "security",
       "Reviews the permission model for over-grants.", B.NONE,
       keywords=("permission", "access control", "rbac")),
    _s("security_recommendations", "Security Recommendations", C.SECURITY, "security",
       "Concrete hardening guidance ranked by impact.", B.LLM,
       keywords=("harden", "secure", "recommendation")),

    # -------------------------------------------------------------- vision
    _s("image_recognition", "Image Recognition", C.VISION, "vision",
       "Identifies the contents of an image.", B.VISION_MODEL,
       keywords=("image", "picture", "photo")),
    _s("object_detection", "Object Detection", C.VISION, "vision",
       "Locates and labels objects within an image.", B.VISION_MODEL,
       keywords=("detect", "objects")),
    _s("face_analysis", "Face Analysis", C.VISION, "vision",
       "Detects faces and their attributes.", B.VISION_MODEL,
       keywords=("face", "faces")),
    _s("ocr", "OCR", C.VISION, "ocr",
       "Extracts text from images and scans.", B.OCR_ENGINE,
       keywords=("ocr", "extract text", "scanned")),
    _s("screenshot_understanding", "Screenshot Understanding", C.VISION, "vision",
       "Reads and explains a captured screen.", B.VISION_MODEL,
       keywords=("screenshot", "screen capture")),
    _s("ui_analysis", "UI Analysis", C.VISION, "vision",
       "Critiques interface layout and hierarchy.", B.VISION_MODEL,
       keywords=("ui", "interface", "layout review")),
    _s("diagram_analysis", "Diagram Analysis", C.VISION, "vision",
       "Interprets architecture and flow diagrams.", B.VISION_MODEL,
       keywords=("diagram", "flowchart")),
    _s("chart_analysis", "Chart Analysis", C.VISION, "vision",
       "Reads values and trends from charts.", B.VISION_MODEL,
       keywords=("chart", "graph", "plot")),
    _s("scene_understanding", "Scene Understanding", C.VISION, "vision",
       "Describes the overall context of an image.", B.VISION_MODEL),
    _s("image_captioning", "Image Captioning", C.VISION, "vision",
       "Generates a concise caption for an image.", B.VISION_MODEL,
       keywords=("caption", "describe image")),

    # --------------------------------------------------------------- audio
    _s("speech_recognition", "Speech Recognition", C.AUDIO, "audio",
       "Converts speech to text.", B.STT_ENGINE,
       keywords=("speech to text", "listen")),
    _s("speaker_detection", "Speaker Detection", C.AUDIO, "audio",
       "Distinguishes between speakers in a recording.", B.STT_ENGINE,
       keywords=("speaker", "diarisation")),
    _s("noise_reduction", "Noise Reduction", C.AUDIO, "audio",
       "Cleans background noise from audio.", B.STT_ENGINE),
    _s("audio_analysis", "Audio Analysis", C.AUDIO, "audio",
       "Characterises an audio recording.", B.STT_ENGINE),
    _s("voice_emotion", "Voice Emotion Detection", C.AUDIO, "voice",
       "Infers emotional tone from text and speech.", B.NONE,
       keywords=("emotion", "tone")),
    _s("audio_transcription", "Audio Transcription", C.AUDIO, "audio",
       "Produces a full transcript of a recording.", B.STT_ENGINE,
       keywords=("transcribe", "transcript")),
    _s("audio_summarization", "Audio Summarization", C.AUDIO, "audio",
       "Summarises a transcript into key points.", B.STT_ENGINE),

    # --------------------------------------------------------------- video
    _s("video_analysis", "Video Analysis", C.VIDEO, "vision",
       "Analyses video content frame by frame.", B.VIDEO_TOOLS,
       keywords=("video", "clip", "footage")),
    _s("scene_detection", "Scene Detection", C.VIDEO, "vision",
       "Segments video into distinct scenes.", B.VIDEO_TOOLS),
    _s("object_tracking", "Object Tracking", C.VIDEO, "vision",
       "Follows an object across frames.", B.VIDEO_TOOLS),
    _s("subtitle_generation", "Subtitle Generation", C.VIDEO, "audio",
       "Generates timed subtitles from audio.", B.STT_ENGINE,
       keywords=("subtitle", "captions", "srt")),
    _s("timeline_analysis", "Timeline Analysis", C.VIDEO, "vision",
       "Maps events onto a video timeline.", B.VIDEO_TOOLS),
    _s("video_summarization", "Video Summarization", C.VIDEO, "vision",
       "Condenses a video into its key moments.", B.VIDEO_TOOLS),
    _s("motion_detection", "Motion Detection", C.VIDEO, "vision",
       "Identifies movement between frames.", B.VIDEO_TOOLS),

    # ------------------------------------------------------------ document
    _s("pdf_analysis", "PDF Analysis", C.DOCUMENT, "document",
       "Reads and answers questions about PDFs.", B.DOC_PARSER,
       keywords=("pdf",)),
    _s("word_documents", "Word Documents", C.DOCUMENT, "document",
       "Reads DOCX and ODT files.", B.DOC_PARSER,
       keywords=("word", "docx")),
    _s("excel_analysis", "Excel Analysis", C.DOCUMENT, "document",
       "Reads spreadsheets and their formulas.", B.DOC_PARSER,
       keywords=("excel", "spreadsheet", "xlsx")),
    _s("powerpoint_analysis", "PowerPoint Analysis", C.DOCUMENT, "document",
       "Reads slide decks.", B.DOC_PARSER,
       keywords=("powerpoint", "slides", "pptx")),
    _s("markdown_analysis", "Markdown Analysis", C.DOCUMENT, "document",
       "Reads and restructures Markdown.", B.NONE,
       keywords=("markdown", "md")),
    _s("text_extraction", "Text Extraction", C.DOCUMENT, "document",
       "Pulls plain text out of a document.", B.NONE,
       keywords=("extract text",)),
    _s("table_extraction", "Table Extraction", C.DOCUMENT, "document",
       "Recovers tabular data from documents.", B.DOC_PARSER,
       keywords=("table", "tabular")),
    _s("document_summarization", "Document Summarization", C.DOCUMENT, "document",
       "Condenses a document to its essentials.", B.LLM,
       keywords=("summarise document", "summarize document")),
    _s("document_comparison", "Document Comparison", C.DOCUMENT, "document",
       "Highlights differences between two documents.", B.LLM,
       keywords=("compare documents", "diff document")),

    # ----------------------------------------------------------------- web
    _s("web_browsing", "Web Browsing", C.WEB, "web",
       "Fetches public pages.", B.NETWORK,
       keywords=("browse", "open url", "fetch page")),
    _s("information_retrieval", "Information Retrieval", C.WEB, "research",
       "Finds and organises relevant knowledge.", B.LLM,
       keywords=("find out", "look up")),
    _s("research", "Research", C.WEB, "research",
       "Gathers and synthesises knowledge on a topic.", B.LLM,
       keywords=("research", "investigate")),
    _s("web_scraping", "Web Scraping", C.WEB, "web",
       "Extracts structured data from pages.", B.NETWORK,
       keywords=("scrape", "extract from site")),
    _s("website_analysis", "Website Analysis", C.WEB, "web",
       "Reviews a site's structure and content.", B.NETWORK),
    _s("api_exploration", "API Exploration", C.WEB, "web",
       "Probes and documents an HTTP API.", B.NETWORK,
       keywords=("explore api", "api docs")),
    _s("documentation_search", "Documentation Search", C.WEB, "research",
       "Searches technical documentation.", B.LLM,
       keywords=("docs", "documentation search")),

    # ----------------------------------------------------------- workspace
    _s("project_analysis", "Project Analysis", C.WORKSPACE, "workspace",
       "Understands project structure and conventions.", B.NONE,
       keywords=("project", "codebase")),
    _s("folder_analysis", "Folder Analysis", C.WORKSPACE, "workspace",
       "Summarises the contents of a directory.", B.NONE,
       keywords=("folder", "directory")),
    _s("file_organization", "File Organization", C.WORKSPACE, "workspace",
       "Proposes and applies a file structure.", B.NONE,
       keywords=("organise files", "organize files")),
    _s("dependency_detection", "Dependency Detection", C.WORKSPACE, "workspace",
       "Identifies project dependencies and versions.", B.NONE,
       keywords=("dependencies", "packages")),
    _s("project_context", "Project Context Building", C.WORKSPACE, "workspace",
       "Feeds project knowledge into the memory graph.", B.NONE,
       background=True),
    _s("workspace_search", "Workspace Search", C.WORKSPACE, "workspace",
       "Searches files and symbols in the open project.", B.NONE,
       keywords=("find file", "search project")),
    _s("automatic_indexing", "Automatic Indexing", C.WORKSPACE, "workspace",
       "Indexes files and symbols in the background.", B.NONE,
       background=True),

    # ---------------------------------------------------------- automation
    _s("workflow_automation", "Workflow Automation", C.AUTOMATION, "automation",
       "Designs and runs multi-step workflows.", B.NONE,
       keywords=("automate", "workflow")),
    _s("scheduled_tasks", "Scheduled Tasks", C.AUTOMATION, "scheduler",
       "Runs work on a schedule.", B.NONE,
       keywords=("schedule", "every day", "cron")),
    _s("batch_processing", "Batch Processing", C.AUTOMATION, "automation",
       "Applies an operation across many items.", B.NONE,
       keywords=("batch", "bulk")),
    _s("macro_execution", "Macro Execution", C.AUTOMATION, "automation",
       "Replays a recorded sequence of actions.", B.NONE,
       keywords=("macro",)),
    _s("file_automation", "File Automation", C.AUTOMATION, "automation",
       "Automates file moves, renames and cleanup.", B.NONE),
    _s("command_automation", "Command Automation", C.AUTOMATION, "terminal",
       "Chains shell commands into a workflow.", B.TERMINAL),

    # ------------------------------------------------------- communication
    _s("translation", "Translation", C.COMMUNICATION, "translation",
       "Translates between twenty-plus languages.", B.LLM,
       keywords=("translate", "in spanish", "in french")),
    _s("grammar_correction", "Grammar Correction", C.COMMUNICATION, "translation",
       "Corrects grammar while preserving voice.", B.LLM,
       keywords=("grammar", "proofread")),
    _s("writing_assistance", "Writing Assistance", C.COMMUNICATION, "writing",
       "Drafts and improves prose.", B.LLM,
       keywords=("write", "draft", "rephrase")),
    _s("email_drafting", "Email Drafting", C.COMMUNICATION, "writing",
       "Composes email in the requested register.", B.LLM,
       keywords=("email", "reply to")),
    _s("technical_writing", "Technical Writing", C.COMMUNICATION, "writing",
       "Produces precise technical prose.", B.LLM,
       keywords=("technical writing", "spec")),
    _s("report_generation", "Report Generation", C.COMMUNICATION, "writing",
       "Builds structured reports from findings.", B.LLM,
       keywords=("report",)),
    _s("meeting_summaries", "Meeting Summaries", C.COMMUNICATION, "writing",
       "Condenses notes or transcripts into actions.", B.LLM,
       keywords=("meeting", "minutes")),

    # ------------------------------------------------------------------ ai
    _s("prompt_optimization", "Prompt Optimization", C.AI, "reasoning",
       "Rewrites prompts for better model output.", B.LLM,
       keywords=("prompt",)),
    _s("model_selection", "Model Selection", C.AI, "core",
       "Picks the right model for each task kind.", B.NONE, background=True),
    _s("local_llm_management", "Local LLM Management", C.AI, "core",
       "Detects and health-checks local runtimes.", B.NONE, background=True),
    _s("cloud_model_routing", "Cloud Model Routing", C.AI, "core",
       "Routes to cloud providers with failover.", B.NONE, background=True),
    _s("multi_agent_coordination", "Multi-Agent Coordination", C.AI, "collaboration",
       "Plans handoffs between specialist agents.", B.LLM,
       keywords=("coordinate", "multiple agents")),
    _s("response_evaluation", "Response Evaluation", C.AI, "reasoning",
       "Judges whether an answer actually addresses the request.", B.LLM),
    _s("self_reflection", "Self-Reflection", C.AI, "reasoning",
       "Reviews its own reasoning for gaps.", B.LLM,
       keywords=("reflect", "critique yourself")),
    _s("tool_selection", "Tool Selection", C.AI, "core",
       "Chooses which agent or skill serves a request.", B.NONE, background=True),

    # ------------------------------------------------------------ learning
    _s("preference_learning", "Preference Learning", C.LEARNING, "personalization",
       "Records and applies stated preferences.", B.NONE,
       keywords=("i prefer", "remember that i")),
    _s("conversation_learning", "Conversation Learning", C.LEARNING, "learning",
       "Learns from prior exchanges.", B.NONE, background=True),
    _s("workflow_learning", "Workflow Learning", C.LEARNING, "learning",
       "Recognises repeated sequences worth automating.", B.NONE, background=True),
    _s("skill_improvement", "Skill Improvement", C.LEARNING, "learning",
       "Tracks which skills succeed and which fail.", B.NONE, background=True),
    _s("context_adaptation", "Context Adaptation", C.LEARNING, "learning",
       "Adjusts behaviour to the active project.", B.NONE, background=True),
    _s("pattern_recognition", "Pattern Recognition", C.LEARNING, "learning",
       "Surfaces recurring themes in memory.", B.NONE,
       keywords=("pattern", "trend")),

    # -------------------------------------------------------------- device
    _s("pc_monitoring", "PC Monitoring", C.DEVICE, "device",
       "Live CPU, RAM, disk and network readings.", B.NONE,
       background=True, keywords=("cpu", "ram", "system usage")),
    _s("phone_integration", "Phone Integration", C.DEVICE, "device",
       "Pairs with and manages a mobile device.", B.DEVICE_LINK,
       keywords=("phone", "mobile")),
    _s("hardware_detection", "Hardware Detection", C.DEVICE, "device",
       "Identifies host CPU, GPU and memory.", B.NONE,
       keywords=("hardware", "gpu", "specs")),
    _s("performance_optimization", "Performance Optimization", C.DEVICE, "performance",
       "Recommends changes based on live metrics.", B.LLM,
       keywords=("optimise", "optimize", "slow")),
    _s("resource_monitoring", "Resource Monitoring", C.DEVICE, "monitoring",
       "Watches resource pressure continuously.", B.NONE, background=True),
    _s("notification_management", "Notification Management", C.DEVICE, "notification",
       "Routes and formats user notifications.", B.NONE),

    # ------------------------------------------------------------ creative
    _s("image_generation", "Image Generation", C.CREATIVE, "vision",
       "Generates images from a description.", B.IMAGE_MODEL,
       keywords=("generate image", "draw", "render")),
    _s("uiux_suggestions", "UI/UX Suggestions", C.CREATIVE, "writing",
       "Proposes interface and interaction improvements.", B.LLM,
       keywords=("ux", "design suggestion")),
    _s("threed_workflow", "3D Workflow Assistance", C.CREATIVE, "writing",
       "Guidance for Blender and similar 3D tools.", B.LLM,
       keywords=("blender", "3d", "modelling")),
    _s("design_assistance", "Design Assistance", C.CREATIVE, "writing",
       "Visual and layout guidance.", B.LLM,
       keywords=("design",)),
    _s("story_writing", "Story Writing", C.CREATIVE, "writing",
       "Narrative and creative prose.", B.LLM,
       keywords=("story", "fiction", "narrative")),
    _s("brainstorming", "Brainstorming", C.CREATIVE, "reasoning",
       "Generates and sorts ideas.", B.LLM,
       keywords=("brainstorm", "ideas")),

    # -------------------------------------------------------- productivity
    _s("calendar_planning", "Calendar Planning", C.PRODUCTIVITY, "planning",
       "Schedules work across available time.", B.LLM,
       keywords=("calendar", "schedule meeting")),
    _s("task_management", "Task Management", C.PRODUCTIVITY, "planning",
       "Tracks tasks and their state.", B.LLM,
       keywords=("todo", "task list")),
    _s("notes_organization", "Notes Organization", C.PRODUCTIVITY, "memory",
       "Files notes into the memory graph.", B.NONE,
       keywords=("notes", "note")),
    _s("project_tracking", "Project Tracking", C.PRODUCTIVITY, "planning",
       "Monitors progress against a plan.", B.LLM,
       keywords=("progress", "tracking")),
    _s("reminder_suggestions", "Reminder Suggestions", C.PRODUCTIVITY, "scheduler",
       "Proposes reminders from context.", B.NONE,
       keywords=("remind",)),
    _s("priority_management", "Priority Management", C.PRODUCTIVITY, "planning",
       "Ranks work by impact and urgency.", B.LLM,
       keywords=("priority", "prioritise", "prioritize")),

    # -------------------------------------------------------------- system
    _s("background_monitoring", "Background Monitoring", C.SYSTEM, "monitoring",
       "Continuous subsystem health checks.", B.NONE, background=True),
    _s("update_management", "Update Management", C.SYSTEM, "update",
       "Tracks component versions and updates.", B.NONE),
    _s("cache_optimization", "Cache Optimization", C.SYSTEM, "performance",
       "Manages cache size and eviction.", B.NONE, background=True),
    _s("performance_analysis", "Performance Analysis", C.SYSTEM, "performance",
       "Analyses latency and throughput.", B.NONE,
       keywords=("performance", "benchmark")),
    _s("diagnostics", "Diagnostics", C.SYSTEM, "monitoring",
       "Reports faults and their likely cause.", B.NONE,
       keywords=("diagnose", "health check")),
    _s("logging", "Logging", C.SYSTEM, "monitoring",
       "Structured logging across subsystems.", B.NONE, background=True),
    _s("backup_restore", "Backup & Restore", C.SYSTEM, "backup",
       "Snapshots and restores the memory graph.", B.NONE,
       keywords=("backup", "restore", "snapshot")),
    _s("recovery_management", "Recovery Management", C.SYSTEM, "backup",
       "Verifies and recovers from a snapshot.", B.NONE,
       keywords=("recover", "recovery")),
)

#: Fast lookup by id.
SKILLS_BY_ID: dict[str, Skill] = {skill.id: skill for skill in SKILLS}


def skills_in(category: SkillCategory | str) -> tuple[Skill, ...]:
    """Every skill in a category."""
    value = SkillCategory(category)
    return tuple(s for s in SKILLS if s.category is value)


def category_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for skill in SKILLS:
        counts[skill.category.value] = counts.get(skill.category.value, 0) + 1
    return counts
