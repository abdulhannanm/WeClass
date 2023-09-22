from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect, Response
from fastapi import *
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
import string
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_permissions_policy_header(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"

    return response


app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# db_config = {
#     "host" : "localhost",
#     "user" : "root",
#     "password": "ffrn1234",
# }



# connection = mysql.connector.connect(**db_config)
# cursor = connection.cursor()





# def create_db():
#     cursor.execute("CREATE DATABASE IF NOT EXISTS chat_db")
#     cursor.execute("USE chat_db")
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS vid_ids (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         room_id TEXT
#     )
#     """)

# create_db()



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
            await connection.send_text(message)


room_dict = {}

def add_room_id():
    nor_res = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    res = str(nor_res)
    # query1 = "select count(*) from vid_ids where room_id = %s"
    # values = (res, )
    # cursor.execute(query1, values)
    # result = cursor.fetchone()
    # if result[0] > 0:
    #     add_room_id()
    # else:
    #     query2 = "INSERT INTO vid_ids (room_id) VALUES(%s)"
    #     values = (res, )
    #     cursor.execute(query2, values)
    #     create_table_query = f"""
    #     CREATE TABLE IF NOT EXISTS {res} (
    #         id INT AUTO_INCREMENT PRIMARY KEY,
    #         message TEXT,
    #         video_timestamp INT,
    #         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    #     """
    #     cursor.execute(create_table_query)
    #     connection.commit()
    return res

@app.get("/api/analytics")
async def get_analytics_data():

    analytics_data = [
        {
            "roomID": "room1",
            "clientID": "client1",
            "timestamp": "2023-09-22 12:00:00",
            "message": "Hello from client 1",
        },
        {
            "roomID": "room1",
            "clientID": "client2",
            "timestamp": "2023-09-22 12:05:00",
            "message": "Hi there from client 2",
        },

    ]

    return JSONResponse(content=analytics_data)            





# def get_messages_for_room(room_id):
#     query = f'SELECT * FROM {room_id}'
#     cursor.execute(query)
#     results = cursor.fetchall()
#     return results

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
    # messages = get_messages_for_room(room_id)
    # print(messages)
    messages = '';
    return templates.TemplateResponse("video.html", 
    {"request": request, 
    "video_title": video_title, 
    "profname": profname, 
    "url": video_url, 
    "messages":messages,
    "room_id": room_id})

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