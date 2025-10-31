# AI Agent with GitHub Integration

> Made for Северсталь-Инфоком as testing task

# How to Run

Firstly, set environment variable `OPENAI_API_KEY` and get `credentials.json` for Google API. To get this file you need:

- go to [Google Cloud Console](https://console.cloud.google.com/)
- create new project and setup Mail and Calendar API
- add new user and setup OAuth
- retrieve json file from OAuth
- store the file as `credentials.json` in ./sever-test/deployment

Then,

```bash
cd sever-test/deployment
docker-compose up --build
```

You can access system on `http://localhost:8000` for the first time to set up Google Intergration.

Then, u can use just `http://localhost:3000`.

# Architecture

```
User → Frontend
         ↓ WebSocket
       Backend
         ↓ WebSocket
       OpenAI Realtime API
         ↓
       Backend (executes tool)
         ↓
       Gmail API / Calendar API
         ↓
       Backend
         ↓
       OpenAI → Backend → Frontend → User
```

# Constrains

- Save one context and one api key at a time
- UI shows all the messages (system also) - better debug btw
- If audio stucks - reload page)
