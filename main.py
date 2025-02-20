import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from db import init_db, get_sesion
from app_models import User
import motor.motor_asyncio
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")
db_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://root:example@localhost:27017/")
message_db = db_client["chat_app"]
message_collection = message_db["messages"]

init_db()
def get_current_user(request: Request):
    user = request.cookies.get("session_user")
    if not user:
        raise HTTPException(status_code=403, detail="Non sei autenticato")
    return user

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.api_route("/register", methods=["GET", "POST"])
async def register(
    request: Request,
    session: Session = Depends(get_sesion),
    name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    number_phone: int = Form(None),
    password: str = Form(None)
):
    if request.method == "POST":
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Email già registrata!"})
        user = User(name=name, last_name=last_name, email=email, number_phone=number_phone, password=password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return templates.TemplateResponse("register.html", {"request": request, "message": "Registrazione completata!"})
    return templates.TemplateResponse("register.html", {"request": request})

@app.api_route("/login", methods=["GET", "POST"])
async def login(
    request: Request,
    session: Session = Depends(get_sesion),
    name: str = Form(None),
    password: str = Form(None)
):
    if request.method == "POST":
        user = session.exec(select(User).where(User.name == name)).first()
        if user and user.password == password:
            response = RedirectResponse(url="/profile", status_code=303)
            response.set_cookie(key="session_user", value=user.name)
            return response
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenziali errate"})
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_user")
    return response

@app.get("/profile")
async def profile(request: Request, user: str = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.get("/all_users")
async def all_users(request: Request, user: str = Depends(get_current_user), session: Session = Depends(get_sesion)):
    current_user = session.exec(select(User).where(User.name == user)).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    all_profiles = session.exec(select(User).where(User.id != current_user.id)).all()
    return templates.TemplateResponse("profiles.html", {"request": request, "all_profiles": all_profiles})

@app.get("/messages/{recipient}")
async def get_or_create_chat(
    request: Request,
    recipient: str,
    user: str = Depends(get_current_user),
    session: Session = Depends(get_sesion)
):
    recipient_user = session.exec(select(User).where(User.id == int(recipient))).first()
    if not recipient_user:
        raise HTTPException(status_code=404, detail="Utente destinatario non trovato")
    recipient_username = recipient_user.name
    messages = await message_collection.find({
        "$or": [
            {"sender": user, "receiver": recipient_username},
            {"sender": recipient_username, "receiver": user}
        ]
    }).sort("timestamp", 1).to_list(length=100)

    if not messages:
        system_message = {
            "sender": "Sistema",
            "receiver": user,
            "message": f"Inizia una chat con {recipient_username}!",
            "timestamp": None
        }
        await message_collection.insert_one(system_message)
        messages.append(system_message)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "user": user,
        "recipient": recipient_username, 
        "messages": messages
    })

class ConnectionManager:
    def __init__(self):
        self.active_connections = {} 

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        if username not in self.active_connections:
            self.active_connections[username] = []
        self.active_connections[username].append(websocket)

    def disconnect(self, username: str, websocket: WebSocket):

        if username in self.active_connections:
            self.active_connections[username].remove(websocket)
            if not self.active_connections[username]:
                del self.active_connections[username]

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            disconnected_sockets = []
            for ws in self.active_connections[username]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    disconnected_sockets.append(ws)
            for ws in disconnected_sockets:
                self.disconnect(username, ws)


manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    print(f"[DEBUG] WebSocket aperto per: {username}")
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_json()
            sender = data["sender"]
            receiver = data["receiver"]
            message_text = data["message"]

            message = {
                "sender": sender,
                "receiver": receiver,
                "message": message_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            result = await message_collection.insert_one(message)
            if result.inserted_id:
                message["_id"] = result.inserted_id
            safe_message = message.copy()
            if "_id" in safe_message:
                safe_message["_id"] = str(safe_message["_id"])
            await manager.send_personal_message(safe_message, receiver)
            await manager.send_personal_message(safe_message, sender)
    except WebSocketDisconnect:
        manager.disconnect(username, websocket)

def start():
    uvicorn.run(app, host="127.0.0.1", port=8003)

if __name__ == "__main__":
    start()
