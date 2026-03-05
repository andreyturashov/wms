# AI Agents

This document describes the AI agent capabilities for the WMS (Workflow Management System).

## Agent Types

### 1. Executor
- Executes task automation, scheduling, and notifications
- Automatically categorizes and prioritizes new tasks
- Monitors task deadlines and sends reminders
- Routes tasks to appropriate columns based on keywords

### 2. Thinker
- Analyses tasks, provides recommendations, and generates insights
- Generates productivity reports and identifies bottlenecks
- Helps create new tasks with natural language
- Provides task recommendations and smart deadline estimation

## Agent Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│    API      │────▶│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  AI Agents  │
                    └─────────────┘
```

## Future Enhancements

- Integration with LLM (Large Language Models)
- Voice command support
- Automated task scheduling
- Smart deadline estimation
- Team collaboration insights

## Technology Stack

- Python asyncio for concurrent agent processing
- Redis for agent message queues
- Celery for background tasks
- OpenAI/Anthropic APIs for LLM capabilities
