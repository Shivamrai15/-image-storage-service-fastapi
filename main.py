from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.auth
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore, storage
import starlette.status as status
from datetime import datetime
import local_constants

app = FastAPI()


app.mount('/static', StaticFiles(directory='static'), name='static' )
templets = Jinja2Templates(directory='templates')

firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()

@app.get("/", response_class=HTMLResponse)
async def root( request : Request ) :
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    gallery =  getUserGalleries(user_token['user_id'])
    return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : user_token , 'error_message' : error_message, "gallery" : gallery })
    

def validateFirebaseToken(id_token):
    if not id_token:
        return None
    
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    return  user_token


def getUser(user_token):
    user = firestore_db.collection('users').document(user_token['user_id']).get()
    if not user.exists:   
        firestore_db.collection('users').document(user_token['user_id']).create({
            "email" : user_token['email'],
            "createdAt" : datetime.now()
        })
        user = firestore_db.collection('users').document(user_token['user_id']).get()
    return user



def addFile(file):
    storage_client = storage.Client( project = local_constants.PROJECT_NAME )
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = storage.Blob(file.filename, bucket)
    blob.upload_from_file(file.file)
    blob.make_public()
    return blob.public_url


def getUserGalleries (userId):
    try:
        existedGalleries = firestore_db.collection('gallery').where('userId', "==", userId).get()
        return existedGalleries
    except:
        return []
    

def getGalleryImages ( galleryId : str ) :
    try:
        images = firestore_db.collection('images').where('galleryId', "==", galleryId).get()
        if len(images) == 0:
            return None
        return images
    except:
        return None
    

@app.post("/create-gallery", response_class=HTMLResponse)
async def createGallery( request:Request ):
    try:
        id_token = request.cookies.get("token")
        error_message = "No error here"
        user_token = None
        user_token = validateFirebaseToken(id_token)
        if not user_token :
            return RedirectResponse("/")
        
        form = await request.form()
        existedGalleries = getUserGalleries(user_token['user_id'])
        for gallery in existedGalleries:
            if gallery.get("name") == form['name']:
                return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

        firestore_db.collection('gallery').document().set({
            "name" : form['name'],
            "userId" : user_token['user_id'],
            "createdAt" : datetime.now()
        })
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        print("Exception", e)
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@app.get("/gallery/{id}")
async def getGallery( request : Request, id:str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    gallery = firestore_db.collection('gallery').document(id).get()
    if not gallery.exists:
        return RedirectResponse("/")

    if gallery.get('userId') != user_token['user_id']:
        return RedirectResponse("/")
    
    images = getGalleryImages(galleryId=gallery.id)

    return templets.TemplateResponse('gallery.html', { 'request' : request, 'user_token': user_token, "gallery": gallery, "images": images })



@app.get("/gallery/update/{id}")
async def getGallery( request : Request, id:str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })

    gallery = firestore_db.collection('gallery').document(id).get()
    if not gallery.exists:
        return RedirectResponse("/")

    if gallery.get('userId') != user_token['user_id']:
        return RedirectResponse("/")
    
    return templets.TemplateResponse('update-gallery.html', { 'request' : request, 'user_token': user_token, "gallery": gallery })



@app.post("/gallery/update/{id}")
async def updateGallery( request : Request, id:str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })

    
    form = await request.form()
    existedGalleries = getUserGalleries(user_token['user_id'])
    for gallery in existedGalleries:
            if gallery.get("name") == form['name']:
                return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


    gallery = firestore_db.collection('gallery').document(id)
    if not gallery.get().exists:
        return RedirectResponse("/")

    if gallery.get().get('userId') != user_token['user_id']:
        return RedirectResponse("/")
    
    gallery.update({
        "name" : form['name']
    })
    
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@app.get("/gallery/delete/{id}", response_class=RedirectResponse)
async def deleteGallery ( request: Request, id: str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    gallery = firestore_db.collection('gallery').document(id)
    if not gallery.get().exists:
        return RedirectResponse("/")

    if gallery.get().get('userId') != user_token['user_id']:
        return RedirectResponse("/")
    
    gallery.delete()

    return RedirectResponse("/")


@app.post("/upload/{id}", response_class=RedirectResponse)
async def uploadImage ( request: Request, id: str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    gallery = firestore_db.collection('gallery').document(id)
    if not gallery.get().exists:
        return RedirectResponse("/")
    
    form = await request.form()
    url = addFile(form['image'])

    firestore_db.collection('images').document().set({
        "image" : url,
        "filename" : form['image'].filename,
        "galleryId" : id,
        "userId" : user_token['user_id'],
        "createdAt" : datetime.now()
    })
    
    return RedirectResponse(f"/gallery/{id}", status_code=status.HTTP_302_FOUND)


@app.get("/delete-image/{id}", response_class=RedirectResponse)
async def deleteImage( request: Request, id:str ):
    id_token = request.cookies.get("token")
    error_message = None
    user_token = None
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    image = firestore_db.collection('images').document(id)
    if not image.get().exists:
        return RedirectResponse("/")
    
    if image.get().get('userId') != user_token['user_id']:
        return RedirectResponse("/")
    
    galleryId = image.get().get("galleryId")
    image.delete()

    return RedirectResponse(f"/gallery/{galleryId}", status_code=status.HTTP_302_FOUND)



    