
from typing import Optional
from numpy import BUFSIZE
from starlette.requests import Request
from fastapi import FastAPI, Response, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()
origins = ["*"]
BUFSIZE = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


uploads = {}


def get_chunk_name(uploaded_filename, chunk_number):
    return uploaded_filename + "_part_%03d" % chunk_number


@app.get("/upload")
def read_root(request: Request, response: Response):
    ridentifier = str(request.query_params["resumableIdentifier"])
    rfilename = str(request.query_params["resumableFilename"])
    rchunknum = int(request.query_params["resumableChunkNumber"])
    if not ridentifier or not rfilename or not rchunknum:
        response.status_code = 500
        return "Parameter error"

    temp_dir = os.path.join(os.getcwd(), ridentifier)
    chunk_file = os.path.join(temp_dir, get_chunk_name(rfilename, rchunknum))
    print("Getting chunk: ", chunk_file)

    if os.path.isfile(chunk_file):
        return "OK"
    else:
        response.status_code = 404
        return "Not found"


def save_chunk(file, data):
    with open(file, "wb+", buffering=BUFSIZE) as file_object:
        file_object.write(data)
    return


@app.post("/upload")
def read_item(request: Request, file: UploadFile = File(...)):
    ridentifier = request.query_params["resumableIdentifier"]
    rfilename = request.query_params["resumableFilename"]
    rchunknum = int(request.query_params["resumableChunkNumber"])
    rtotalchunks = int(request.query_params["resumableTotalChunks"])

    chunk_data = file.file
    temp_dir = os.path.join(os.getcwd(), ridentifier)
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    chunk_name = get_chunk_name(rfilename, rchunknum)
    chunk_file = os.path.join(temp_dir, chunk_name)
    # print(chunk_file)
    # chunk_data.save(chunk_file)
    save_chunk(chunk_file, chunk_data.read())

    # check if upload is complete
    chunk_paths = [os.path.join(temp_dir, get_chunk_name(
        rfilename, x)) for x in range(1, rtotalchunks+1)]
    upload_complete = all([os.path.exists(p) for p in chunk_paths])

    # combile all chunks to create file
    if upload_complete:

        target_file_name = os.path.join(os.getcwd(), "now", rfilename)
        with open(target_file_name, "ab", buffering=BUFSIZE) as target_file:
            for p in chunk_paths:
                stored_chunk_file_name = p
                stored_chunk_file = open(
                    stored_chunk_file_name, 'rb', buffering=BUFSIZE)
                target_file.write(stored_chunk_file.read())
                stored_chunk_file.close()
                # os.unlink(stored_chunk_file_name)
        target_file.close()
        print("file saved in :", target_file_name)
    total_chunks_completed = len(os.listdir(temp_dir))
    return {"status": "ok", "progress": (total_chunks_completed/rtotalchunks)*100}
