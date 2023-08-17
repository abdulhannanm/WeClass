from typing import Union, List
from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL
from pydantic import BaseModel
import mysql.connector
import random
import string


app = FastAPI()


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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            message TEXT,
            video_timestamp INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

create_db()



class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def broadcast(self, data: str):
        for connection in self.connections:
            await connection.send_text(data)


manager = ConnectionManager()

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
        connection.commit()
    return res


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    while True:
        data = await websocket.receive_text()
        print(data)
        await manager.broadcast(f"{data}")




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
    return '/video/'+profname+"/"+video_title+"/"+new_url+'/'+room_id

@app.get("/video/{profname}/{video_title}/{new_url}/{room_id}", response_class=HTMLResponse)
async def read_item(request: Request, profname: str, video_title: str, new_url: str, room_id: str):
    video_url = "https://www.youtube.com/embed/" + new_url + "?enablejsapi=1"
    print(video_url)
    return templates.TemplateResponse("video.html", {"request": request, "video_title": video_title, "profname": profname, "url": video_url})
    


if __name__ == "__main__":
    uvicorn.run("fastapi_code:app")