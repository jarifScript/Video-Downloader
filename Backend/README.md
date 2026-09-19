# Video Downloader API

FastAPI backend for the video downloader, packaged as a Docker service for Render.

## Deploy on Render

1. Create a new **Blueprint** from this repository. Render will use the root `render.yaml` file.
2. Set `CORS_ORIGINS` to the public URL of the deployed frontend. For local development, use `http://localhost:5173`.
3. Deploy the service. Render provides the `PORT` environment variable; the Docker image listens on it automatically.

The health check is available at `/health`. Downloaded files are temporary and are removed after they are sent to the client, so no persistent disk is required.

## Local Docker run

```bash
docker build -t video-downloader-api ./Backend
docker run --rm -p 10000:10000 -e PORT=10000 video-downloader-api
```
