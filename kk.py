import os
import subprocess
import threading
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# لتخزين عمليات البث حسب tag
processes = {}
lock = threading.Lock()

class StreamData(BaseModel):
    input: str
    vf_filter: str
    output: str
    tag: str

@app.post("/start_stream")
async def start_stream(data: StreamData):
    with lock:
        if data.tag in processes:
            return {"error": "هذا البث يعمل مسبقاً"}

        # بناء أمر ffmpeg
        cmd = [
            "ffmpeg",
            "-re",
            "-i", data.input,
            "-vf", data.vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-f", "flv",
            data.output
        ]

        # تشغيل ffmpeg في subprocess
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # تخزين العملية
        processes[data.tag] = proc

        return {"status": "started", "tag": data.tag}

@app.post("/stop_stream")
async def stop_stream(request: Request):
    data = await request.json()
    tag = data.get("tag")

    with lock:
        proc = processes.get(tag)
        if not proc:
            return {"error": "لا يوجد بث بهذا الوسم"}

        proc.terminate()
        proc.wait()
        del processes[tag]

        return {"status": "stopped", "tag": tag}

@app.get("/status")
async def status():
    with lock:
        running = list(processes.keys())
    return {"running_streams": running}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)