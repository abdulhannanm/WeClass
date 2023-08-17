from typing import Union, List
from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL
from pydantic import BaseModel


app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")

#from fastapi import FastAPI

#app = FastAPI()

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
    return '/video/'+profname+"/"+video_title+"/"+new_url

@app.get("/video/{profname}/{video_title}/{new_url}", response_class=HTMLResponse)
async def read_item(request: Request, profname: str, video_title: str, new_url: str):
    video_url = "https://www.youtube.com/embed/" + new_url + "?enablejsapi=1"
    print(video_url)
    return templates.TemplateResponse("video.html", {"request": request, "video_title": video_title, "profname": profname, "url": video_url})
    


if __name__ == "__main__":
    uvicorn.run("fastapi_code:app")