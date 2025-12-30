
import asyncio
import logging
import os
import ffmpeg
from google import genai
from google.genai import types

# Real Gemini Implementation

logger = logging.getLogger("uvicorn")

class TranscriptionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
        else:
            logger.warning("GEMINI_API_KEY not found in environment. Transcription will fail.")

    async def stream_transcription(self, audio_chunk_iterator):
        """
        Streams audio to Gemini Live API via FFmpeg PCM conversion.
        """
        if not self.client:
            yield {"error": "API Key missing or invalid"}
            return

        logger.info("Starting Gemini Live transcription stream")
        process = None

        try:
            # FFmpeg: Convert Input Stream (WebM/WAV) -> PCM 16kHz s16le
            process = (
                ffmpeg
                .input('pipe:0')
                .output('pipe:1', format='s16le', acodec='pcm_s16le', ac=1, ar='16000')
                .run_async(pipe_stdin=True, pipe_stdout=True, stderr=asyncio.subprocess.DEVNULL)
            )
        except Exception as e:
            logger.error(f"FFmpeg start failed: {e}")
            yield {"error": "Audio Transcoding failed (ffmpeg issue?)"}
            return

        config = {"response_modalities": ["TEXT"]}

        try:
            # Connect to Gemini Live
            async with self.client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
                
                # 1. Sender Task: PCM -> Gemini
                async def sender_loop():
                    try:
                        while True:
                            # 4KB chunk ~ 128ms audio
                            chunk = await asyncio.to_thread(process.stdout.read, 4096)
                            if not chunk:
                                break
                            await session.send(input={"data": chunk, "mime_type": "audio/pcm"}, end_of_turn=False)
                    except Exception as e:
                        logger.error(f"Sender Loop Error: {e}")

                # 2. Writer Task: WS -> FFmpeg
                async def writer_loop():
                    try:
                        async for chunk in audio_chunk_iterator:
                            if chunk:
                                process.stdin.write(chunk)
                                process.stdin.flush()
                        process.stdin.close()
                    except Exception as e:
                        logger.error(f"Writer Loop Error: {e}")
                        try: process.stdin.close() 
                        except: pass

                # Start background tasks
                sender_task = asyncio.create_task(sender_loop())
                writer_task = asyncio.create_task(writer_loop())

                # 3. Receiver Loop (Main): Gemini -> Client
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.text:
                                    yield {"text": part.text}
                except Exception as e:
                     logger.error(f"Receiver Error: {e}")
                     yield {"error": "Connection to AI lost"}
                finally:
                    # Cancel background tasks if receiver loop ends
                    sender_task.cancel()
                    writer_task.cancel()
                
        except Exception as e:
            logger.error(f"Gemini Session Error: {e}")
            yield {"error": f"AI Error: {str(e)}"}
        finally:
            if process:
                 try: process.kill() 
                 except: pass

    async def transcribe_file(self, file_path: str, format: str):
        """
        Full file transcription using generate_content
        """
        if not self.client:
            raise Exception("API Key missing")

        logger.info(f"Transcribing file: {file_path} (Format: {format})")
        
        # Mapping extension to mime type
        mime_map = {
            'webm': 'audio/webm',
            'wav': 'audio/wav',
            'mp3': 'audio/mp3',
            'm4a': 'audio/mp4',
            'ogg': 'audio/ogg'
        }
        mime_type = mime_map.get(format, 'audio/webm')

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Part.from_bytes(data=file_content, mime_type=mime_type),
                    "Generate a detailed transcript of this audio. Identify different speakers (Speaker A, Speaker B, etc.) if detectable."
                ]
            )
            
            return {
                "transcript": response.text,
                "language": "en" # Metadata
            }

        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            raise e

transcription_service = TranscriptionService()
