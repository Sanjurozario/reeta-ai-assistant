import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.gateway import model_gateway, GatewayMessage
from app.core.tasks import broadcaster, TaskManager
from app.database.session import async_session_factory
from app.permissions.service import PermissionService

logger = logging.getLogger("reeta.websocket")
ws_router = APIRouter(tags=["WebSockets"])


@ws_router.websocket("/ws/v1/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    Primary real-time bidirectional event bus:
    - Streams LLM thoughts, plan generation, tool calls, and verification events to desktop client.
    - Receives user prompt interactions, ticket decisions, cancellations, and emergency stops.
    """
    await websocket.accept()
    broadcaster.connect(websocket)
    logger.info("Desktop client connected to /ws/v1/stream")

    try:
        # Welcome frame
        await websocket.send_json({
            "event": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "REETA WebSocket event bus connected successfully."},
        })

        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "payload": {"message": "Invalid JSON frame."}})
                continue

            event_type = data.get("event", "")
            payload = data.get("payload", {})

            # 1. Heartbeat
            if event_type == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {},
                })

            # 2. User Conversational Message
            elif event_type == "user_message":
                text = payload.get("text", "")
                await websocket.send_json({
                    "event": "agent_thought",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"agent": "orchestrator", "thought": f"Analyzing intent: '{text}'"},
                })

                # Route through Model Gateway with fallback
                try:
                    response = await model_gateway.generate_with_fallback(
                        messages=[
                            GatewayMessage(role="system", content="You are REETA, an autonomous personal AI Operating System for Windows 11."),
                            GatewayMessage(role="user", content=text),
                        ]
                    )
                    await websocket.send_json({
                        "event": "agent_message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {
                            "content": response.content,
                            "provider": response.provider,
                            "model": response.model,
                            "latency_ms": response.latency_ms,
                        },
                    })
                except Exception as e:
                    await websocket.send_json({
                        "event": "error",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {"message": f"Generation failed: {e}"},
                    })

            # 3. Task Cancellation
            elif event_type == "task_cancel":
                task_id = payload.get("task_id")
                if task_id:
                    async with async_session_factory() as session:
                        await TaskManager.cancel_task(session, task_id)

            # 4. Human Approval Decision
            elif event_type == "approval_response":
                ticket_id = payload.get("ticket_id")
                decision = payload.get("decision", "reject")
                async with async_session_factory() as session:
                    res = await PermissionService.resolve_ticket(session, ticket_id, decision)
                    await websocket.send_json({
                        "event": "approval_resolved",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": res,
                    })

            # 5. Emergency Stop
            elif event_type == "emergency_stop":
                for tid, worker in list(TaskManager._active_workers.items()):
                    worker.cancel()
                TaskManager._active_workers.clear()
                TaskManager._cancellation_events.clear()
                await broadcaster.broadcast(
                    event="emergency_stop",
                    task_id="system",
                    payload={"message": "Emergency stop initiated from WebSocket."},
                )

    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
        logger.info("Desktop client disconnected from /ws/v1/stream")
    except Exception as e:
        broadcaster.disconnect(websocket)
        logger.error(f"WebSocket error: {e}", exc_info=True)
