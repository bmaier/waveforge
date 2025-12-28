# REST API Documentation

## Overview

WaveForge Pro provides a RESTful API for audio file upload, management, and retrieval. The API is built with FastAPI and follows REST principles.

**Base URL**: `http://localhost:8000`

## Authentication

Currently, the API does not require authentication. Future versions will implement JWT-based authentication.

## Endpoints

### Frontend Routes

#### `GET /`

Serves the main application interface.

**Response**:
- **Type**: `text/html`
- **Content**: Frontend application (index.html)

**Example**:
```bash
curl http://localhost:8000/
```

---

#### `GET /sw.js`

Serves the Service Worker script.

**Response**:
- **Type**: `application/javascript`
- **Content**: Service Worker code

**Example**:
```bash
curl http://localhost:8000/sw.js
```

---

#### `GET /favicon.svg`

Serves the application icon.

**Response**:
- **Type**: `image/svg+xml`
- **Content**: Favicon SVG

**Example**:
```bash
curl http://localhost:8000/favicon.svg
```

---

#### `GET /assets/{path}`

Serves static assets from the public directory.

**Parameters**:
- `path` (path): Path to asset file

**Response**:
- **Type**: Varies (image/*, application/*, etc.)
- **Content**: Requested asset

**Example**:
```bash
curl http://localhost:8000/assets/logo.png
```

---

### Audio Upload API

#### `POST /upload/chunk`

Upload a single chunk of an audio file.

**Content-Type**: `multipart/form-data`

**Form Fields**:
- `file_id` (string, required): Unique identifier for the file (UUID)
- `chunk_index` (integer, required): Zero-based chunk index
- `total_chunks` (integer, required): Total number of chunks for this file
- `file_name` (string, required): Original filename with extension
- `file` (file, required): Binary chunk data

**Response**: `200 OK`
```json
{
  "status": "chunk_received",
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 0,
  "total_chunks": 10
}
```

**Response**: `200 OK` (Final Chunk)
```json
{
  "status": "file_complete",
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_path": "/backend/uploaded_data/recording_20240115_123456.webm",
  "file_size": 10485760
}
```

**Error Response**: `400 Bad Request`
```json
{
  "detail": "Missing required field: file_id"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/upload/chunk \
  -F "file_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -F "chunk_index=0" \
  -F "total_chunks=10" \
  -F "file_name=my_recording.webm" \
  -F "file=@chunk_0.part"
```

**JavaScript Example**:
```javascript
const formData = new FormData();
formData.append('file_id', fileId);
formData.append('chunk_index', chunkIndex);
formData.append('total_chunks', totalChunks);
formData.append('file_name', fileName);
formData.append('file', chunkBlob);

const response = await fetch('/upload/chunk', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result.status); // "chunk_received" or "file_complete"
```

---

### Recording Management API

#### `POST /recording/complete`

Finalize a recording after all chunks are uploaded.

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_name": "my_recording.webm",
  "metadata": {
    "duration": 120.5,
    "sample_rate": 48000,
    "channels": 2,
    "codec": "opus"
  }
}
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "recording_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_path": "/backend/uploaded_data/recording_20240115_123456.webm",
  "metadata": {
    "duration": 120.5,
    "sample_rate": 48000,
    "channels": 2,
    "codec": "opus"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/recording/complete \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_name": "my_recording.webm",
    "metadata": {
      "duration": 120.5,
      "sample_rate": 48000,
      "channels": 2,
      "codec": "opus"
    }
  }'
```

---

#### `GET /recordings`

List all recordings.

**Response**: `200 OK`
```json
{
  "recordings": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "file_name": "my_recording.webm",
      "file_size": 10485760,
      "duration": 120.5,
      "created_at": "2024-01-15T12:34:56Z",
      "metadata": {
        "sample_rate": 48000,
        "channels": 2,
        "codec": "opus"
      }
    }
  ],
  "total": 1
}
```

**Example**:
```bash
curl http://localhost:8000/recordings
```

---

#### `GET /recording/{id}`

Get a specific recording by ID.

**Parameters**:
- `id` (path, required): Recording UUID

**Response**: `200 OK`
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_name": "my_recording.webm",
  "file_path": "/backend/uploaded_data/recording_20240115_123456.webm",
  "file_size": 10485760,
  "duration": 120.5,
  "created_at": "2024-01-15T12:34:56Z",
  "metadata": {
    "sample_rate": 48000,
    "channels": 2,
    "codec": "opus"
  }
}
```

**Response**: `404 Not Found`
```json
{
  "detail": "Recording not found"
}
```

**Example**:
```bash
curl http://localhost:8000/recording/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

#### `DELETE /recording/{id}`

Delete a recording.

**Parameters**:
- `id` (path, required): Recording UUID

**Response**: `200 OK`
```json
{
  "status": "deleted",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response**: `404 Not Found`
```json
{
  "detail": "Recording not found"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/recording/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

#### `GET /recording/{id}/download`

Download a recording file.

**Parameters**:
- `id` (path, required): Recording UUID

**Response**: `200 OK`
- **Type**: `audio/webm` (or appropriate MIME type)
- **Content**: Binary audio file
- **Headers**: `Content-Disposition: attachment; filename="my_recording.webm"`

**Response**: `404 Not Found`
```json
{
  "detail": "Recording not found"
}
```

**Example**:
```bash
curl -O -J http://localhost:8000/recording/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download
```

---

### Health Check API

#### `GET /health`

Health check endpoint for monitoring.

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T12:34:56Z",
  "uptime": 3600,
  "storage": {
    "total_recordings": 42,
    "total_size_mb": 512.5,
    "available_space_mb": 10240.0
  }
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

---

## Upload Flow

### Chunked Upload Process

1. **Client splits file into chunks** (1MB each)
2. **For each chunk**, POST to `/upload/chunk`:
   - Same `file_id` for all chunks
   - Sequential `chunk_index` (0, 1, 2, ...)
   - Same `total_chunks` value
3. **Server receives chunks** and stores in temp directory
4. **After final chunk**, server automatically:
   - Assembles all chunks into final file
   - Moves to completed directory
   - Cleans up temp files
5. **Client receives** `file_complete` response
6. **(Optional)** Client calls `/recording/complete` with metadata

### Example Full Upload

```javascript
async function uploadRecording(blob, fileName) {
  const fileId = generateUUID();
  const chunkSize = 1024 * 1024; // 1MB
  const totalChunks = Math.ceil(blob.size / chunkSize);
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, blob.size);
    const chunk = blob.slice(start, end);
    
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('chunk_index', i);
    formData.append('total_chunks', totalChunks);
    formData.append('file_name', fileName);
    formData.append('file', chunk);
    
    const response = await fetch('/upload/chunk', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    console.log(`Chunk ${i+1}/${totalChunks}: ${result.status}`);
    
    if (result.status === 'file_complete') {
      console.log('Upload complete!', result.file_path);
      return result;
    }
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "detail": "Error message description",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T12:34:56Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 413 | Payload Too Large | File/chunk exceeds size limit |
| 500 | Internal Server Error | Server error occurred |
| 503 | Service Unavailable | Server temporarily unavailable |

### Common Error Codes

- `MISSING_FIELD`: Required field missing from request
- `INVALID_FORMAT`: Invalid file format or data format
- `FILE_TOO_LARGE`: File exceeds maximum size limit
- `CHUNK_OUT_OF_ORDER`: Chunks received in wrong order
- `STORAGE_FULL`: Server storage quota exceeded
- `FILE_NOT_FOUND`: Requested file does not exist

---

## Rate Limiting

**Current**: No rate limiting implemented

**Future**: 
- 100 requests per minute per IP
- 1GB upload per day per IP
- Configurable in server settings

---

## CORS Policy

**Current**: Same-origin only

**Configuration** (in `server.py`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## API Versioning

**Current Version**: v1 (implicit)

**Future**: Explicit versioning via URL prefix
- `/api/v1/upload/chunk`
- `/api/v2/upload/chunk`

---

## WebSocket API (Future)

### `WS /ws/upload`

Real-time upload status updates.

**Client → Server**:
```json
{
  "action": "subscribe",
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Server → Client**:
```json
{
  "event": "chunk_received",
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 5,
  "total_chunks": 10,
  "progress": 50
}
```

---

## Best Practices

### Client Implementation

1. **Generate UUID** for each upload
2. **Use consistent chunk size** (1MB recommended)
3. **Handle network errors** with retry logic
4. **Track upload progress** for user feedback
5. **Validate file types** before upload
6. **Use FormData** for multipart uploads
7. **Implement exponential backoff** for retries

### Server Integration

1. **Validate all inputs** before processing
2. **Use streaming** for large files
3. **Clean up temp files** after assembly
4. **Log all operations** for debugging
5. **Monitor storage usage** to prevent full disk
6. **Set file size limits** appropriately
7. **Implement rate limiting** in production

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Example Client Library

```javascript
class WaveForgeClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }
  
  async uploadRecording(blob, fileName, onProgress) {
    const fileId = this.generateUUID();
    const chunkSize = 1024 * 1024; // 1MB
    const totalChunks = Math.ceil(blob.size / chunkSize);
    
    for (let i = 0; i < totalChunks; i++) {
      const chunk = blob.slice(i * chunkSize, (i + 1) * chunkSize);
      
      const formData = new FormData();
      formData.append('file_id', fileId);
      formData.append('chunk_index', i);
      formData.append('total_chunks', totalChunks);
      formData.append('file_name', fileName);
      formData.append('file', chunk);
      
      const response = await fetch(`${this.baseURL}/upload/chunk`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (onProgress) {
        onProgress({
          uploaded: i + 1,
          total: totalChunks,
          percentage: ((i + 1) / totalChunks) * 100
        });
      }
      
      if (result.status === 'file_complete') {
        return { fileId, ...result };
      }
    }
  }
  
  async getRecordings() {
    const response = await fetch(`${this.baseURL}/recordings`);
    return await response.json();
  }
  
  async deleteRecording(id) {
    const response = await fetch(`${this.baseURL}/recording/${id}`, {
      method: 'DELETE'
    });
    return await response.json();
  }
  
  generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}

// Usage
const client = new WaveForgeClient();

await client.uploadRecording(audioBlob, 'my_recording.webm', (progress) => {
  console.log(`Upload: ${progress.percentage.toFixed(1)}%`);
});
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-15  
**Maintained By**: WaveForge
