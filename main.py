from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pytube import YouTube
from pytube.exceptions import RegexMatchError, VideoUnavailable, PytubeError
from text_recognition import async_text_recognition
from gpt_summary import summary_text, request_message
from moviepy.editor import VideoFileClip
import shutil
import config
import uvicorn
import shutil

app = FastAPI(
    title='Shorten',
    summary="쇼튼(Shorten) FastAPI 서버",
    description='Zzang Ji Sung 의 전폭적인 지원',
    version="0.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],   
    allow_headers=["*"],
)

class URL(BaseModel):
    url: str

class QUESTIONS(BaseModel):
    summary: str
    question: str

@app.get('/')
async def hello_world():
    return {"status":"테스트"}


@app.post("/upload_video/")
async def upload_video(video: UploadFile = File(...)):
    file_extension = await get_file_extension(video.filename)
    if file_extension not in config.ALLOW_TYPE:
        raise HTTPException(status_code=400,
                            detail="'.mp4', '.avi' 또는 '.mkv' 와 같은 확장자의 영상 파일을 업로드해 주세요!")
    
    input_path = f"input/uploaded_vid/input.{file_extension}"
    output_path = "input/uploaded_vid/input.mp3"
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    await extract_audio(input_path, output_path)
    print('음성에서 텍스트를 추출하는 중 입니다...')
    # origin = ['치피치피차파차파', '두비두비다바다바', '마기코비 두비두비', '붐 붐 붐 붐']
    origin = await async_text_recognition('input/uploaded_vid/input.mp3')
    print('추출된 텍스트를 요약하는 중 입니다...')
    # 챗지피티로 요약한 내용 리턴 
    # summed = ''
    summed = summary_text(origin)
    
    
    return JSONResponse(content={"response": "\n".join(origin),
                                 "summary": "".join(summed)})


@app.post("/upload_url/")
async def upload_url(url: URL):
    url = url.url
    try:
        yt = YouTube(url)
        duration_seconds = yt.length
        if duration_seconds > 1800:
            raise HTTPException(status_code=400,
                            detail='영상의 길이가 30분을 초과했습니다!')
        print("유튜브 영상에서 mp3 파일을 다운로드 중...")
        
        yt.streams.filter(only_audio=True).first().download(output_path='input/uploaded_url/',
                                                            filename='input.mp3')
        print('음성에서 텍스트를 추출하는 중 입니다...')
        # origin = ['yee', 'yee']
        origin = await async_text_recognition('input/uploaded_url/input.mp3')
        print('추출된 텍스트를 요약하는 중 입니다...')
        # summed = ''
        summed = summary_text(origin)
         
        # 챗지피티로 요약한 내용 리턴
        return JSONResponse(content={"response": "\n".join(origin),
                                     "summary": "".join(summed)})
    
    # 예외 처리
    except RegexMatchError or PytubeError:
        raise HTTPException(status_code=400,
                            detail='입력하신 유튜브 영상의 URL이 유효하지 않아요!')
    except VideoUnavailable:
        raise HTTPException(status_code=400,
                            detail='해당 동영상을 가져올 수 없습니다.')
    

@app.post('/message_req')
async def message(req: QUESTIONS):
    s = req.summary
    q = req.question
    msg = request_message(s, q)

    return JSONResponse(content={"response": msg})
                            
        
# 파일 확장자 return
async def get_file_extension(filename: str):
    return filename.split(".")[-1]
    

# 비디오 파일에서 음성 파일 추출
async def extract_audio(input_file: str, output_file: str):
    video_clip = VideoFileClip(input_file)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(output_file)
    audio_clip.close()
    video_clip.close()


if __name__ == '__main__':
    uvicorn.run('main:app', port=1557, host='0.0.0.0', reload=True)