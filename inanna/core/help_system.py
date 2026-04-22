"""
Role-aware help system for INANNA NYX.
Returns different help text depending on the user's role and profile.
"""
from __future__ import annotations

# ── HELP CONTENT BY ROLE ──────────────────────────────────────────────────────

HELP_COMMON = """𒀭 INANNA NYX — Available Commands

  CONVERSATION
    Just type naturally — INANNA will respond.
    Use "analyse [question]" for structured reasoning.

  NATURAL LANGUAGE
    INANNA understands your intent regardless of phrasing.
    You do not need exact commands. Examples:

    "anything from Matxalen?"        finds her emails
    "Вїtengo algo urgente?"           checks urgent emails (Spanish)
    "resumeix els correus d'ahir"    yesterday's emails (Catalan)
    "read ~/proposal.pdf"            reads a document
    "search the web for NixOS"       web search
    "what's on my calendar?"         today's events
    "open firefox"                   opens Firefox
    "list my downloads"              filesystem listing

    On fast hardware: NAMMU uses full LLM understanding.
    On slow hardware: NAMMU uses intelligent regex fallback.
    Both produce correct results. Speed differs.

  NAMMU PROFILE (teach INANNA your language)
    nammu-learn mtx Matxalen      Teach shorthand (mtx = Matxalen)
    nammu-learn act Actuavalles   Teach another shorthand
    nammu-correct email_search    Correct the last NAMMU misrouting
    nammu-profile                 Show your current NAMMU profile

    After teaching, INANNA can understand phrases like:
    "mtx replied?"
    Profile grows automatically from every interaction.

  YOUR PROFILE
    my-profile                    Show your profile
    my-profile edit [field] [val] Update a field
    my-profile clear [field]      Clear a field
    my-profile clear communication Clear all observed style data

  GOVERNANCE & TRUST
    my-trust                      Show your persistent trust patterns
    governance-trust [tool]       Mark a tool as persistently trusted
    governance-revoke [tool]      Revoke persistent trust for a tool

  GOVERNANCE (constitutional boundaries)
    The Constitutional Filter runs on every message.
    It holds firm on: harm to minors, WMDs, hate speech,
    audit suppression, genocide incitement.
    It does not block: difficult topics, dark themes,
    questions about INANNA's limitations.

    Type 'nammu-profile' to see your operator profile.
    Type 'status' to see system health.

  ORGANIZATION
    my-departments                Show your departments and groups

  FILES (speak naturally)
    "read the file at ~/notes.txt"
    "list my Documents folder"
    "find all .py files in ~/code"
    "what is the size of ~/report.pdf"
    "write a file called ideas.txt with this content..."
    (all file writes require approval)

  SYSTEM & PROCESSES
    "how is the system doing?"
    "what is using all my memory?"
    "show me python processes"
    "kill process 1234" (requires approval)
    "run echo hello" (requires approval)

  PACKAGES (speak naturally)
    "what packages do I have installed?"
    "search for a text editor"
    "install firefox" (requires approval)
    "remove firefox" (requires approval)

  COMMUNICATION (Signal, WhatsApp)
    "read my Signal messages"          Read messages (no approval)
    "check WhatsApp"                   Read WhatsApp (no approval)
    "list my Signal contacts"          List contacts (no approval)
    "send a message to Maria on Signal saying hello"
                                       Send message (approval x2:
                                       type draft + confirm send)
    (sending ALWAYS requires approval - no exceptions)

  EMAIL (Thunderbird, Proton Mail)
    "check my email"                Read inbox (no approval)
    "read the email from Carlos"    Read specific email (no approval)
    "search my email for invoice"   Search emails (no approval)
    "send an email to..."           Compose draft (approval x2:
                                    compose + confirm send)
    "reply to the email from Sara"  Compose reply (approval x2)
    (sending email ALWAYS requires approval - no exceptions)

  CALENDAR (Thunderbird / Google Calendar)
    "what do I have today"         Today's events (no approval)
    "upcoming events"              Next 7 days (no approval)
    "next 14 days"                 Next 14 days (no approval)
    "read ics file at ~/path.ics"  Read .ics file (no approval)

  Note: Google Calendar events sync via Thunderbird Lightning.
  Open Thunderbird to trigger a sync if events are missing.
  CalDAV direct connection available in future phase.

  DOCUMENTS (LibreOffice, PDF, DOCX, ODT)
    "read the document at ~/path/to/file.pdf"
                                       Read any document (no approval)
    "summarize ~/report.docx"          Summarize document (no approval)
    "write a document called report.txt with..."
                                       Write document (approval required)
    "open ~/proposal.odt in libreoffice"
                                       Open in LibreOffice (approval)
    "export ~/letter.docx to pdf"      Export to PDF (approval)

  Supported: .txt .md .docx .odt .pdf .xlsx .ods .csv
  (reading never requires approval - writing always does)

  BROWSER (Firefox, Chrome, Edge)
    "read the page at https://example.com"
                                       Fetch and read URL (no approval)
    "search the web for NixOS install" Web search (no approval)
    "go to https://example.com"        Open in Firefox (approval)
    "open https://example.com in chrome"
                                       Open in Chrome (approval)

  Note: passwords and financial forms are never accessible
  Internal/local addresses (localhost, 192.168.x.x) are blocked

  DESKTOP (speak naturally)
    "open firefox"                Open any application
    "read the whatsapp window"    Read window content
    "click the Send button"       Click a UI element
    "type hello world"            Type text
    "take a screenshot"           Capture screen
    (consequential send/delete actions always require approval)

  SESSION
    whoami                        Show who you are logged in as
    logout                        End your session
    history                       Show your conversation history
    my-log                        Show your interaction log

  MEMORY
    Memories are written automatically.
    Say "remember this" to explicitly approve a memory.


  SOFTWARE
    software                      List all installed software with launch buttons
    software [name]               Filter by name (e.g. "software firefox")
    "list installed software"     Same via natural language
    "open firefox"                Launch any installed app (requires approval)
    "search for a text editor"    Search available packages with install buttons
    "install vlc"                 Install software (requires approval)
  Type "help [command]" for details on any specific command.
"""

HELP_OPERATOR = """
  OPERATOR COMMANDS
    tool-registry                 View registered tools
    network-status                Live network status
    process-status                Running processes
    routing-log                   NAMMU routing history
    nammu-log                     Full NAMMU log
    memory-log                    Memory record log
    body                          System body status
    status                        Full system status
    diagnostics                   System diagnostics
    audit                         Audit trail
    proposal-history              Full proposal history
    faculty-registry              View all Faculties

  REALM MANAGEMENT
    realms                        List all realms
    realm-context                 Show current realm
    switch-user [name]            Act as another user (Guardian only)

  Console: http://localhost:8080/console
"""

HELP_GUARDIAN = """
  GUARDIAN COMMANDS
    users                         List all users
    create-user [name] [role]     Create a new user
    invite [role] [realm]         Generate an invite code
    invites                       List all invites
    view-profile [name]           View any user's profile
    admin-surface                 Full admin dashboard

  ORGANIZATIONAL MANAGEMENT
    assign-department [user] [dept]   Assign user to department
    unassign-department [user] [dept] Remove user from department
    assign-group [user] [group]       Assign user to group
    unassign-group [user] [group]     Remove user from group
    notify-department [dept] [msg]    Notify all dept members

  REALM ADMINISTRATION
    create-realm [name]           Create a new realm
    assign-realm [user] [realm]   Assign user to realm
    unassign-realm [user] [realm] Remove user from realm

  GOVERNANCE
    guardian                      Run GUARDIAN Faculty inspection
    guardian-dismiss              Dismiss Guardian alerts
    guardian-clear-events         Clear Guardian event log
    inanna-reflect                View INANNA's self-knowledge
    reflect [observation]         Propose a INANNA self-reflection
    approve [proposal_id]         Approve a proposal
    reject [proposal_id]          Reject a proposal
    forget [proposal_id]          Remove a memory record

  SYSTEM
    body                          Full body/health report
    diagnostics                   Deep diagnostics
"""

HELP_ANONYMOUS = """𒀭 INANNA NYX

  You are not logged in.

  GETTING STARTED
    login [name]                  Identify yourself
    join [invite_code]            Join with an invite code

  Ask INANNA anything — she will help even without a profile.
"""

HELP_TOPICS = {
    "my-profile": """my-profile — View and edit your profile

  my-profile                         Show your full profile

  EDIT — use friendly names (no underscores needed):
  my-profile edit name ZAERA           Set your preferred name
  my-profile edit pronouns she/her      Set your pronouns
  my-profile edit city Barcelona        Set your city
  my-profile edit country Spain         Set your country
  my-profile edit timezone Europe/Madrid  Set your timezone
  my-profile edit languages en,es,pt    Set your languages
  my-profile edit gender nonbinary      Set your gender

  CLEAR:
  my-profile clear pronouns             Clear a field
  my-profile clear communication        Clear all style observations

  Friendly field names:
    name / preferred          → preferred_name
    pronouns / pronoun        → pronouns
    city / location_city      → location_city
    country / location_country → location_country
    region / location_region  → location_region
    timezone / tz             → timezone
    language / languages      → languages
    gender                    → gender
    sex                       → sex""",

    "governance-trust": """governance-trust — Persistent tool trust

  governance-trust web_search     Trust web_search permanently
  governance-revoke web_search    Revoke that trust
  my-trust                        See all trusted tools

  When a tool is persistently trusted, INANNA executes it
  without a proposal. The audit trail still records each use.
  Trust can always be revoked.""",

    "inanna-reflect": """inanna-reflect — INANNA's self-knowledge

  inanna-reflect                  Show all reflection entries
  reflect [observation]           Propose a new reflection
                                  (Guardian only — requires approval)

  Reflections are INANNA's approved observations about herself.
  They are stored in inanna/data/self/reflection.jsonl
  and used to ground her responses.""",

    "faculties": """faculties — The Faculties of INANNA NYX

  CROWN      Primary conversational voice. Warm, honest, relational.
  ANALYST    Structured reasoning. Analysis, comparison, logic.
  OPERATOR   Tool execution. web_search, ping, scan_ports, resolve_host,
              read_file, list_dir, file_info, search_files, write_file,
              list_processes, system_info, kill_process, run_command,
              comm_read_messages, comm_send_message, comm_list_contacts,
              email_read_inbox, email_read_message, email_search,
              email_compose, email_reply,
              calendar_today, calendar_upcoming, calendar_read_ics,
              search_packages, list_packages, install_package, remove_package,
              launch_app,
              desktop_open_app, desktop_read_window, desktop_click,
              desktop_type, desktop_screenshot.
  GUARDIAN   System observation. Health, audit, inspection.
  SENTINEL   Security Faculty. CVE analysis, threat reasoning.
              Uses qwen2.5-14b-instruct for deeper security reasoning.

  NAMMU routes your input to the appropriate Faculty automatically.
  Use "faculty-registry" to see the full registry with charters.""",

    "help": """help — This help system

  help               Show commands for your role
  help [topic]       Show details on a specific topic

  Topics: my-profile, nammu-profile, governance-trust, inanna-reflect,
          faculties, tools, files, processes, packages, communication, email, calendar, documents, browser, desktop, memory, realms, departments""",

    "nammu-profile": """nammu-profile - NAMMU operator memory

  nammu-profile                  Show your current NAMMU profile
  nammu-learn mtx Matxalen       Teach a shorthand
  nammu-correct email_search     Correct the last routing

  NAMMU stores:
    - known shorthands
    - language patterns
    - top routed domains
    - recent corrections

  Operator context is prepended to NAMMU's prompt as:
    [OPERATOR CONTEXT]
    ...
    [END CONTEXT]

  This context enriches routing without replacing the universal prompt.""",

    "tools": """tools — Available tools (all require proposal approval)

  web_search [query]   Search the web for current information
  ping [host]          Check if a host is reachable
  resolve_host [host]  Resolve hostname to IP address
  scan_ports [host]    Scan ports 1-100 on a host
  launch_app [app]     Launch an installed application

  Observation tools may run without approval.
  Governance:
    - web_search, ping, resolve_host, scan_ports: approval required
    - list_processes, system_info: no approval required
    - kill_process, run_command: approval required
    - comm_read_messages, comm_list_contacts: no approval required
    - comm_send_message: ALWAYS requires approval and send confirmation
    - email_read_inbox, email_read_message, email_search: no approval required
    - email_compose, email_reply: ALWAYS require approval and send confirmation
    - search_packages, list_packages: no approval required
    - install_package, remove_package, launch_app: approval required
    - desktop_read_window, desktop_screenshot: no approval required
    - desktop_open_app, desktop_type: approval required
    - desktop_click: approval required for consequential labels

  To trust a tool permanently: governance-trust [tool_name]
  To see registered tools: tool-registry""",

    "files": """files вЂ” File system operations

  INANNA can read, list, search, and write files.
  Speak naturally or use direct requests.

  Read a file:    "read the file at ~/path/to/file.txt"
  List a folder:  "list the files in ~/Documents"
  Find files:     "find all .txt files in ~/notes"
  File info:      "what is the size of ~/report.pdf"
  Write a file:   "write a file called todo.txt with..."

  Governance:
    - list, info, search: no approval required
    - read: approval required for paths outside home directory
    - write: ALWAYS requires approval
    - delete: not available (by design)

  Max file read: 512 KB
  Max search results: 50 files
  Max directory listing: 100 entries""",

    "processes": """processes вЂ” Process and system operations

  INANNA can inspect the running system and, with approval,
  act on processes or run a shell command.

  System health:    "how is the system doing?"
  Process list:     "show me python processes"
  Memory pressure:  "what is using all my memory?"
  Kill by pid:      "kill process 1234"
  Run command:      "run echo hello"

  Governance:
    - list_processes, system_info: no approval required
    - kill_process: ALWAYS requires approval
    - run_command: ALWAYS requires approval
    - elevation is not allowed through run_command

  Process observation is for readable system truth.
  Process action remains governed.""",

    "packages": """packages РІР‚вЂќ Package management

  INANNA can inspect installed software and, with approval,
  ask the system package manager to install or remove packages.

  List installed:   "what packages do I have installed?"
  Search software:  "search for a text editor"
  Install package:  "install firefox"
  Remove package:   "remove firefox"

  Governance:
    - search_packages, list_packages: no approval required
    - install_package: ALWAYS requires approval
    - remove_package: ALWAYS requires approval

  Package actions are routed through the detected system manager:
  NixOS, apt, brew, or winget.""",

    "communication": """communication - Messaging workflows

  INANNA can read messages, list visible contacts, and prepare
  governed drafts in supported communication apps.

  Read messages:   "read my Signal messages"
  Check inbox:     "check WhatsApp"
  List contacts:   "list my Signal contacts"
  Send message:    "send a message to Maria on Signal saying hello"

  Governance:
    - comm_read_messages: no approval required
    - comm_list_contacts: no approval required
    - comm_send_message: ALWAYS requires approval twice

  Sending is a two-stage flow:
    1. Approve typing the draft
    2. Approve clicking Send after the draft is visible

  Supported now: Signal and WhatsApp workflows
  Future phases: Telegram, Discord, Slack.""",

    "email": """email - Email workflows

  INANNA can inspect inboxes, read specific messages, search mail,
  compose drafts, and prepare governed replies in desktop email clients.

  Read inbox:      "check my email"
  Read message:    "read the email from Carlos"
  Search mail:     "search my email for invoice"
  Compose draft:   "send an email to maria@example.com about budget saying hello"
  Reply draft:     "reply to the email from Sara saying I will answer tomorrow"

  Governance:
    - email_read_inbox, email_read_message, email_search: no approval required
    - email_compose, email_reply: ALWAYS require approval twice

  Sending is a two-stage flow:
    1. Approve composing the visible draft
    2. Approve clicking Send after you review it

  Supported now: Thunderbird and Proton Mail Desktop
  Future phases: Evolution and Geary.""",

    "calendar": """calendar - Calendar Faculty

  INANNA can read Thunderbird's local calendar cache, summarize upcoming
  events, and parse .ics files directly from disk.

  Today's events:  "what do I have today"
  Upcoming week:   "upcoming events"
  Next 14 days:    "next 14 days"
  Read ICS file:   "read ics file at ~/calendar/invite.ics"

  Governance:
    - calendar_today: no approval required
    - calendar_upcoming: no approval required
    - calendar_read_ics: no approval required

  Important:
    - Thunderbird stores a local cache, not the full Google Calendar truth
    - If the cache is empty, open Thunderbird Calendar to trigger a sync
    - INANNA explains zero local events with that context instead of inventing absence""",

    "documents": """documents - Document Faculty

  INANNA can read documents directly from the file system and,
  with approval, write new documents, open them in LibreOffice,
  or export them to PDF.

  Read a document:  "read the document at ~/proposal.pdf"
  Summarize one:    "summarize ~/report.docx"
  Write one:        "write a document called notes.txt with..."
  Open in office:   "open ~/draft.odt in libreoffice"
  Export to PDF:    "export ~/letter.docx to pdf"

  Supported read formats:
    .txt .md .docx .odt .pdf .xlsx .ods .csv

  Governance:
    - doc_read: no approval required
    - doc_write: approval required
    - doc_open: approval required
    - doc_export_pdf: approval required

  Direct reading is the primary path.
  LibreOffice is only used when opening or exporting documents.""",

    "browser": """browser - Browser Faculty

  INANNA can read public web pages directly, search DuckDuckGo HTML
  results, and with approval open URLs in Firefox, Chrome, or Edge.

  Read a page:      "read the page at https://example.com"
  Fetch a page:     "fetch example.com/docs"
  Search the web:   "search the web for NixOS install"
  Open visibly:     "go to https://example.com"
  Open in Chrome:   "open https://example.com in chrome"

  Governance:
    - browser_read: no approval required
    - browser_search: no approval required
    - browser_open: approval required

  Blocked by design:
    - localhost and private-network URLs
    - file:// URLs
    - passwords and financial forms""",

    "desktop": """desktop - Desktop Faculty operations

  INANNA can bridge into desktop applications through accessibility tools.
  These are app-agnostic primitives, not app-specific workflows.

  Open an app:      "open firefox"
  Read a window:    "read the whatsapp window"
  Click an element: "click the Send button"
  Type text:        "type hello world"
  Screenshot:       "take a screenshot"

  Governance:
    - desktop_read_window, desktop_screenshot: no approval required
    - desktop_open_app: approval required
    - desktop_type: approval required
    - desktop_click: approval required for consequential labels

  Consequential labels include Send, Delete, Submit, Confirm, Buy, and Publish.
  Linux support is stubbed for the later NixOS phase.""",

    "memory": """memory - How INANNA remembers

  Memory is written automatically at session end and every 20 turns.
  No approval is needed for routine conversation recording.

  Proposals are required for:
    - "remember this" — explicit memory requests
    - clear-memory — clearing all memory
    - forget [id] — removing a specific record

  Your profile is separate from memory. Profile grows through
  interaction (CommunicationObserver) and your edits.
  Memory is conversation context. Profile is who you are.""",

    "departments": """departments — Organizational context

  my-departments                    Show your departments and groups
  assign-department [user] [dept]   (Guardian only)
  unassign-department [user] [dept] (Guardian only)
  notify-department [dept] [msg]    (Guardian only)

  When you belong to a department, Guardian can send notifications
  that appear as system messages when you next open a session.
  Departments also affect which realm events INANNA routes to you.""",
}


def build_help_response(role: str, topic: str = "") -> str:
    """Build the role-appropriate help response."""
    topic = topic.strip().lower()

    # Specific topic help
    if topic and topic in HELP_TOPICS:
        return f"INANNA NYX — {topic.upper()}\n\n{HELP_TOPICS[topic]}"

    if topic:
        available = ", ".join(sorted(HELP_TOPICS.keys()))
        return f"help > Unknown topic: {topic}\nAvailable topics: {available}"

    # Role-based full help
    if not role or role == "anonymous":
        return HELP_ANONYMOUS

    base = HELP_COMMON

    if role in ("operator", "guardian"):
        base += HELP_OPERATOR

    if role == "guardian":
        base += HELP_GUARDIAN

    return base
