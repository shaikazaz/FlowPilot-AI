# FlowPilot AI
### AI-Powered Support Ticket Management System

FlowPilot AI is a web-based support ticket management system that combines Django REST Framework, React, and local AI models to simplify issue reporting, ticket management, and company-policy assistance.

## Features

### User / Employee
- User registration and login.
- Submit issues through a simple interface.
- AI-assisted ticket generation.
- View personal support tickets.
- Track ticket status and AI-generated priority.
- View resolutions provided by the Owner.
- Ask questions using the Policy AI assistant.

### Owner / Admin
- View and manage support tickets.
- Update ticket status and priority.
- Add resolutions to reported issues.
- Delete tickets.
- View ticket analytics.

### AI Capabilities
- Local LLM integration using Ollama and Qwen2.5 3B for ticket generation.
- Retrieval-Augmented Generation (RAG) for company-policy question answering.
- FastEmbed embeddings using `BAAI/bge-small-en-v1.5`.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, Django, Django REST Framework |
| Database | SQLite |
| AI / LLM | Ollama, Qwen2.5 3B |
| RAG / Embeddings | FastEmbed, BGE Small English |
| API Communication | REST API, JSON |
| Authentication | Django REST Framework Token Authentication |
| Version Control | Git, GitHub |

## Architecture

```text
User / Owner
     |
     v
React Frontend (Vite)
     |
     | HTTP / REST API
     v
Django REST Framework
     |
     +---- Authentication & Permissions
     |
     +---- Ticket Management
     |
     +---- AI Ticket Generation
     |          |
     |          v
     |       Ollama / Qwen2.5 3B
     |
     +---- Policy AI / RAG
     |          |
     |          v
     |       PDF Retrieval
     |       FastEmbed
     |       LLM Response
     |
     v
SQLite Database
```

## Project Structure

```text
FlowPilot-AI/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── requests/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── ticket_service.py
│   ├── ticket_worker.py
│   ├── rag_service.py
│   └── rag_worker.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── manage.py
└── README.md
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/shaikazaz/FlowPilot-AI.git
cd FlowPilot-AI
```

### 2. Backend setup

```bash
python -m venv .venv
```

Activate the environment on Windows:

```bash
.venv\Scripts\activate
```

Install the Python dependencies required by the project.

Configure the required environment variables and local AI services before running the backend.

Run migrations:

```bash
python manage.py migrate
```

Start Django:

```bash
python manage.py runserver
```

Backend:

`http://127.0.0.1:8000/`

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend:

`http://localhost:5173/`

## Future Improvements

- Production deployment and scalable database configuration.
- Enhanced ticket assignment and workflow automation.
- Improved analytics and reporting.
- Expanded company-policy document support.
- Additional AI-powered support capabilities.

## Author

**Shaik Azaz**

GitHub: https://github.com/shaikazaz

---

*Developed as an AI-powered full-stack application combining backend development, frontend integration, and retrieval-augmented generation.*