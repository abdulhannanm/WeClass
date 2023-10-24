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
import datetime
from decouple import config

app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware, 
    allow_origins = origins, 
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

db_config = {
    "host" : config("DB_HOST"),
    "user" : config("DB_USER"),
    "password": config("DB_PASSWORD"),
    "port":3307,
}


try:
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    print("connection established")
except mysql.connector.Error as err:
    print(f"Error: {err}")





def create_db():
    cursor.execute("CREATE DATABASE IF NOT EXISTS weclass")
    cursor.execute("USE weclass")
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
            clientName = parsed_data.get('clientName')
            msgID = parsed_data.get("msgID")
            if '/@' in msg:
                find_reply(roomID, timestamp, msg, clientID, clientName, msgID)
            else:
                add_messages_to_room(roomID, timestamp, msg, clientID, clientName, msgID)
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
            msgid TEXT,
            clientname TEXT,
            message TEXT,
            video_timestamp INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    return res

def add_messages_to_room(roomID, timestamp, message, clientID, clientName, msgID):
    print("I AM ALSO BEING CALLED")
    check_query = f"SELECT COUNT(*) FROM {roomID} WHERE clientid = %s AND clientname = %s AND video_timestamp = %s AND message = %s"
    cursor.execute(check_query, (clientID, clientName, timestamp, message))
    result = cursor.fetchone()

    if result and result[0] == 0:
        insert_query = f"INSERT INTO {roomID} (clientid, msgid, clientname, message, video_timestamp) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (clientID, msgID, clientName, message, timestamp))    
        connection.commit()

def get_messages_from_room(room_id):
    query = f'SELECT clientid, clientname, video_timestamp, message, msgid FROM {room_id} ORDER BY timestamp'
    cursor.execute(query)
    results = cursor.fetchall()
    return results

def find_reply(roomID, timestamp, message, clientID, clientName, msgID):
    print('hi')
    msg_list = message.split()
    old_msg_id = msg_list[0]
    msg_id = old_msg_id[2:]
    check_query = f"SELECT COUNT(*) FROM {roomID} WHERE msgid = %s"
    cursor.execute(check_query, (msgID, ))
    record = cursor.fetchone()[0]
    print(record)
    if record == 0: 
        timestamp_query = f'SELECT timestamp FROM {roomID} WHERE msgid = %s'
        cursor.execute(timestamp_query, (msg_id,))
        timestamp_of_msg = cursor.fetchone()
        print(timestamp_of_msg)
        if timestamp_of_msg:
            timestamp_of_msg = timestamp_of_msg[0]
            insert_query = f"INSERT INTO {roomID} (clientid, msgid, clientname, message, video_timestamp, timestamp) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (clientID, msgID, clientName, message, timestamp, timestamp_of_msg + datetime.timedelta(seconds=1)))
            connection.commit()
            print('Insert successful')
        else:
            print("No message with that ID")
    else:
        print("record with msgID already exists")


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
    redirectUrl = '/video/'+profname+"/"+video_title+"/"+new_url+'/'+room_id+'/teacher'
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


@app.get("/video/{profname}/{video_title}/{new_url}/{room_id}/teacher", response_class=HTMLResponse)
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
    
    return templates.TemplateResponse("teachervideo.html", 
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