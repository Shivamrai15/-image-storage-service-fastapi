from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()


app.mount('/static', StaticFiles(directory='static'), name='static' )
templets = Jinja2Templates(directory='templates')


@app.get("/", response_class=HTMLResponse)
async def root( request : Request ) :
    id_token = request.cookies.get("token")
    error_message = "No error here"
    user_token = None
    return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })