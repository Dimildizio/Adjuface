# app.py
from fastapi import FastAPI, UploadFile, File,Request
from style_transfer import transfer_style
from tempfile import NamedTemporaryFile
from fastapi.responses import StreamingResponse
import io

app = FastAPI()


@app.post("/style_transfer")
async def style_transfer(request: Request):
    data = await request.json()
    print(data.get("greeting", "No greeting found"))
    return {"message": "Received"}

#app.post("/style_transfer1")
async def style_transfer_api1(content_file: UploadFile = File(...), style_image_path: str = 'lisafacebig.png'):
    print('WORKING')
    with NamedTemporaryFile(delete=False, suffix='.png') as tempfile:
        contents = await content_file.read()
        tempfile.write(contents)
        content_img_path = tempfile.name

    stylized_image = transfer_style(content_img_path, style_image_path)

    # Convert stylized image to bytes and create a streaming response
    img_byte_arr = io.BytesIO()
    stylized_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    return StreamingResponse(io.BytesIO(img_byte_arr), media_type="image/png")
