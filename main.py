from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect, Response
from fastapi import *
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
import string
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import mysql
import mysql.connector
import json

app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.middleware("http")
# async def add_permissions_policy_header(request: Request, call_next):
#     response: Response = await call_next(request)
#     response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"

#     return response


app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

db_config = {
    "host" : "localhost",
    "user" : "root",
    "password": "ffrn1234",
}



connection = mysql.connector.connect(**db_config)
cursor = connection.cursor()





def create_db():
    cursor.execute("CREATE DATABASE IF NOT EXISTS chat_db")
    cursor.execute("USE chat_db")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vid_ids (
        id INT AUTO_INCREMENT PRIMARY KEY,
        room_id TEXT
    )
    """)

create_db()



class Room:
    def __init__(self):
        self.connections = {}

    def add_connection(self, client_id, websocket):
        self.connections[client_id] = websocket
    
    def remove_connection(self, client_id):
        if client_id in self.connections:
            del self.connections[client_id]

    async def broadcast(self, message, sender):
        for client_id, connection in self.connections.items():
            print(message)
            parsed_data = json.loads(message)
            roomID = parsed_data.get("roomID")
            timestamp = parsed_data.get('timestamp')
            msg = parsed_data.get('message')
            clientID = parsed_data.get('clientID')
            add_messages_to_room(roomID, timestamp, msg, clientID)
            await connection.send_text(message)


room_dict = {}




def add_room_id():
    nor_res = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    res = str(nor_res)
    query1 = "select count(*) from vid_ids where room_id = %s"
    values = (res, )
    cursor.execute(query1, values)
    result = cursor.fetchone()
    if result[0] > 0:
        add_room_id()
    else:
        query2 = "INSERT INTO vid_ids (room_id) VALUES(%s)"
        values = (res, )
        cursor.execute(query2, values)
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {res} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            clientid TEXT,
            message TEXT,
            video_timestamp INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    return res

def add_messages_to_room(roomID, timestamp, message, clientID):
    check_query = f"SELECT COUNT(*) FROM {roomID} WHERE clientid = %s AND video_timestamp = %s AND message = %s"
    cursor.execute(check_query, (clientID, timestamp, message))
    result = cursor.fetchone()

    if result and result[0] == 0:
        insert_query = f"INSERT INTO {roomID} (clientid, message, video_timestamp) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (clientID, message, timestamp))    
        connection.commit()

@app.get("/api/analytics", response_class=JSONResponse)
async def get_analytics_data():

    analytics_data = [
        {
            "roomID": "room1",
            "clientID": "Jay Rajesh",
            "timestamp": "2023-09-22 00:01:40",
            "message": "2",
        },
        {
            "roomID": "room1",
            "clientID": "AbdulHannan",
            "timestamp": "2023-09-22 00:00:20",
            "message": "2",
        }

    ]

    return JSONResponse(content=analytics_data)    

@app.get("/analytics")
async def get_analytics_page(request:Request):
    return templates.TemplateResponse("analytics.html", {'request':request})     





def get_messages_from_room(room_id):
    query = f'SELECT clientid, video_timestamp, message FROM {room_id}'
    cursor.execute(query)
    results = cursor.fetchall()
    return results

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, room_id: str):

    try:
        await websocket.accept()
        if room_id not in room_dict:
            room_dict[room_id] = Room()
        room = room_dict[room_id]
        room.add_connection(client_id, websocket)

        print(f"connection established for {client_id} in room {room_id}")

        while True:
            data = await websocket.receive_text()
            await room.broadcast(data, websocket)
    except WebSocketDisconnect:
        print("reset has happened")
        if room_id in room_dict:
            room = room_dict[room_id]
            room.remove_connection(client_id)


@app.on_event("shutdown")
async def shutdown_event():
    for room_id in room_dict:
        room = room_dict[room_id]
        for connection in room.connections:
            try:
                await connection.close()
            except Exception as e:
                print(f"error during closing: {e}")





@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get('/create')
def create(request: Request):
    return templates.TemplateResponse("generic.html", {"request": request})


@app.get('/prof')
def profform(request: Request):
    return templates.TemplateResponse("prof.html", {"request": request})

@app.get('/inprog')
def prog(request: Request):
    return templates.TemplateResponse('inprog.html', {"request": request})
    

@app.get('/about')
def prog(request: Request):
    return templates.TemplateResponse('about.html', {"request": request})
    


@app.post("/submitform", response_class=RedirectResponse, status_code=302)
async def handle_form(video_title: str = Form(...), url: str = Form(...), profname: str = Form(...)):
    print(video_title)
    print(url)
    list_comp = [i for i in url]
    new_url = ''.join(list_comp[32:43])
    print(new_url)
    print(profname)
    room_id = add_room_id()
    print(room_id)
    redirectUrl = '/video/'+profname+"/"+video_title+"/"+new_url+'/'+room_id
    print(redirectUrl)
    return redirectUrl


@app.get("/video/{profname}/{video_title}/{new_url}/{room_id}", response_class=HTMLResponse)
async def read_item(request: Request, profname: str, video_title: str, new_url: str, room_id: str):
    video_url = "https://www.youtube.com/embed/" + new_url + "?enablejsapi=1"
    stored_messages = get_messages_from_room(room_id)
    print(stored_messages)
    messages = '';
    def format_timestamp(timestamp):
        hours = 0
        minutes = 0
        seconds = timestamp
        while seconds >= 60:
            seconds -= 60
            minutes += 1
        while minutes >= 60:
            minutes -= 60
            hours += 1
        return f"{minutes:01d}:{seconds:02d}"
    
    return templates.TemplateResponse("video.html", 
    {"request": request, 
    "video_title": video_title, 
    "profname": profname, 
    "url": video_url, 
    "messages":messages,
    "room_id": room_id,
    "stored_messages": stored_messages, 
    'formatTimestamp': format_timestamp})

@app.on_event("shutdown")
async def shutdown_event():
    for room_id in room_dict:
        room = room_dict[room_id]
        for connection in room.connections:
            try:
                await connection.close()
            except Exception as e:
                print(f"error during closing: {e}")

    


if __name__ == "__main__":
    uvicorn.run("main:app")