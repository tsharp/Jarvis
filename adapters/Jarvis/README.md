# Jarvis Adapter & WebUI

A specialized adapter and web interface for the assistant. Jarvis is designed to be the primary, "native" interface for the `assistant-proxy`, offering deep integration with the system's 3-layer architecture.

## Overview

Jarvis consists of two main parts:
1.  **Backend Adapter**: A FastAPI-based service that translates the custom Jarvis API format to the Core Bridge.
2.  **Web Frontend**: A single-page HTML/JS application acting as a dashboard for interacting with the assistant and configuring the system.

## Backend Adapter (`adapter.py`, `main.py`)

### Purpose
To provide a low-overhead, optimized API endpoint for the Jarvis frontend. Unlike the LobeChat adapter (which mimics OpenAI), Jarvis uses a custom JSON format that exposes more system internals (like Layer metadata).

### API Endpoints
- **POST `/chat`**: Accepts a simple JSON query and returns a response with metadata.
    - **Request**:
        ```json
        {
          "query": "Hello",
          "conversation_id": "user_1",
          "stream": true
        }
        ```
    - **Response**:
        ```json
        {
          "response": "Hi there!",
          "done": true,
          "metadata": { "model": "llama3.1:8b", "memory_used": true }
        }
        ```
- **GET `/health`**: Simple status check.

## Frontend (`index.html`, `static/`)

A sophisticated dashboard providing real-time visibility into the assistant's thought process.

### Key Features
- **Layer Visualization**: Real-time status indicators ("traffic lights") for Thinking, Control, and Output layers.
- **Quick Modes**: Switch between "Fast" (skip layers), "Balanced", and "Accurate".
- **Deep Configuration**: A tabbed settings modal allowing granular control over:
    - **Layers**: Toggle individual layers, select models, adjust temperature.
    - **Memory**: Configure retrieval thresholds (Top-K) and graph walk parameters.
    - **Advanced**: Network settings, validation rules.
- **Quick Actions**: Toolbar for common tasks like clearing memory or regenerating responses.

### Upgrade Notes (v2.0.0)
The frontend recently underwent a major overhaul (Phase 1 Implemented). Key improvements include:
- Tabbed settings instead of a long list.
- Responsive design updates.
- Visual feedback for system status.

### Task-Loop Stream Notes
- The new `static/js/chat-taskloop.js` viewer is driven by `task_loop_update` events plus normal `content` chunks.
- `task_loop_update` may contain multiple `event_types`; the frontend must process all of them in order, not only the first one.
- `task_loop_update` now also carries serialized `events`, so the frontend can map each block (`plan`, `thinking`, `tool`, `reflection`, `finish`, `error`) from the real event payload instead of only a shared snapshot.
- Task-loop step execution now also emits a separate `task_loop_thinking` transport event. This is distinct from the global orchestration `thinking_stream` and should be routed only into the active task-loop block.
- Step bodies are filled from the live `content` stream while a task-loop step is active. The task-loop event itself is primarily the routing/state signal; the streamed text still comes over `content`.
- While a task-loop is running, intermediate step text should stay in the task-loop work view. Only the final task-loop output is mirrored into the normal assistant chat transcript.
- Goal of the current frontend bridge: keep the animated task-loop boxes and the normal assistant transcript in sync, so step containers do not render as empty shells.

## Usage

### Running the Adapter
The Jarvis backend typically runs as part of the `assistant-proxy` docker-compose stack.
```bash
python -m adapters.jarvis.main
```

### Accessing the UI
Serve the `index.html` file using any static file server (e.g., Nginx, Python http.server) or open it directly if configured to talk to the backend.
