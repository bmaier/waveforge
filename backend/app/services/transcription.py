
import asyncio
import logging
import random

# Initial mock implementation using a simple generator
# Later, this will be replaced/extended with Real Google Gemini or Whisper

logger = logging.getLogger("uvicorn")

class TranscriptionService:
    def __init__(self):
        self.is_active = True

    async def stream_transcription(self, audio_chunk_iterator):
        """
        Simulates live transcription.
        Yields text segments.
        In a real scenario, this would send audio chunks to Gemini/Whisper stream
        and yield results.
        """
        logger.info("Starting live transcription stream")
        
        simulated_texts = [
            "Hello,", " this is a", " live transcription", " test.", 
            " waiting for more audio...", " ok, resuming.", " The weather", 
            " is nice today.", " formatting check:", " *Speaker 1*"
        ]
        
        try:
            async for chunk in audio_chunk_iterator:
                # In a real impl, we'd process the chunk here.
                # For now, we simulate processing time and return a random text bit
                # based on chunk size or just periodically.
                
                # Check if chunk is valid audio bytes
                if len(chunk) > 0:
                    await asyncio.sleep(0.01) # Simulate latency (FAST)
                    
                    if True: # Always yield text for testing
                        text = random.choice(simulated_texts)
                        yield {"text": text, "is_final": False}
                        
        except Exception as e:
            logger.error(f"Error in transcription stream: {e}")
            yield {"error": str(e)}

    async def transcribe_file(self, file_path: str, format: str):
        """
        Post-processing transcription for a complete file.
        Returns the full transcript text.
        """
        logger.info(f"Transcribing file: {file_path} (format: {format})")
        
        # Simulate processing time
        await asyncio.sleep(2.0)
        
        # Mock result
        return {
            "transcript": f"This is a generated post-processing transcript for {file_path}. \n\n[Speaker A]: It works perfectly with format {format}.",
            "language": "en",
            "duration": 12.5
        }

# Singleton instance
transcription_service = TranscriptionService()
