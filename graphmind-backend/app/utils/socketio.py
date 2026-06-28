import socketio
from typing import Optional

# Socket.io server for real-time updates
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)

# Store active connections
connected_clients = {}


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    token = None
    if auth and "token" in auth:
        token = auth["token"]
    elif "HTTP_AUTHORIZATION" in environ:
        auth_header = environ["HTTP_AUTHORIZATION"]
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if token:
        connected_clients[sid] = token
        print(f"Client connected: {sid}")
    else:
        print(f"Client connected without auth: {sid}")


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    if sid in connected_clients:
        del connected_clients[sid]
    print(f"Client disconnected: {sid}")


@sio.event
async def join_repository(sid, data):
    """Join a repository room for updates."""
    repo_id = data.get("repository_id")
    if repo_id:
        await sio.enter_room(sid, f"repo_{repo_id}")
        print(f"Client {sid} joined repo {repo_id}")


@sio.event
async def leave_repository(sid, data):
    """Leave a repository room."""
    repo_id = data.get("repository_id")
    if repo_id:
        await sio.leave_room(sid, f"repo_{repo_id}")


async def emit_progress(repository_id: str, stage: str, progress: int, message: str):
    """Emit progress update to all clients watching a repository."""
    await sio.emit(
        "analysis_progress",
        {
            "repository_id": repository_id,
            "stage": stage,
            "progress": progress,
            "message": message,
        },
        room=f"repo_{repository_id}",
    )


async def emit_analysis_complete(repository_id: str, success: bool, message: str = ""):
    """Emit analysis completion event."""
    await sio.emit(
        "analysis_complete",
        {
            "repository_id": repository_id,
            "success": success,
            "message": message,
        },
        room=f"repo_{repository_id}",
    )


# ASGI app for Socket.io
socketio_asgi_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")