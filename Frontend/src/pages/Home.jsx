import { useState } from 'react';
import SEO from '../../components/SEO';
import './Home.css';

const API_URL = 'http://localhost:8000';

function formatDuration(duration) {
    const totalSeconds = Number(duration);
    if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return 'Unknown';

    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);
    const parts = [];

    if (hours) parts.push(`${hours} hr`);
    if (minutes) parts.push(`${minutes} min`);
    if (seconds || parts.length === 0) parts.push(`${seconds} sec`);

    return parts.join(' ');
}

export default function Home() {
    const [url, setUrl] = useState('');
    const [resolution, setResolution] = useState('720');
    const [video, setVideo] = useState(null);
    const [loading, setLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('Working...');
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [error, setError] = useState('');

    async function pasteUrl() {
        try {
            const pastedUrl = await navigator.clipboard.readText();
            setUrl(pastedUrl);
            setError('');
        } catch {
            setError('Unable to access the clipboard. Please paste the URL manually.');
        }
    }

    async function getVideoInfo(event) {
        event.preventDefault();
        setLoading(true);
        setLoadingMessage('Reading video information...');
        setError('');
        setVideo(null);

        try {
            const response = await fetch(`${API_URL}/api/info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Unable to read this video.');
            setVideo(data);
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
            setLoadingMessage('Working...');
        }
    }

    async function waitForDownload(jobId) {
        let pollingAttempts = 0;

        while (true) {
            const response = await fetch(`${API_URL}/api/download/${jobId}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Download status unavailable.');

            if (data.status === 'completed') {
                setDownloadProgress(100);
                return data;
            }
            if (data.status === 'failed') throw new Error(data.error || 'Download failed.');

            if (data.status === 'queued') {
                setDownloadProgress(8);
                setLoadingMessage('Download queued...');
            } else {
                pollingAttempts += 1;
                setDownloadProgress(Math.min(90, 12 + pollingAttempts * 4));
                setLoadingMessage('Downloading...');
            }
            await new Promise((resolve) => setTimeout(resolve, 1000));
        }
    }

    async function downloadVideo() {
        setLoading(true);
        setLoadingMessage('Queueing download...');
        setDownloadProgress(4);
        setError('');

        try {
            const response = await fetch(`${API_URL}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, resolution: resolution ? Number(resolution) : null }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Download failed.');

            const completedDownload = await waitForDownload(data.job_id);
            window.location.assign(`${API_URL}${completedDownload.download_url}`);
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
            setLoadingMessage('Working...');
            setDownloadProgress(0);
        }
    }

    return (
        <>
            <SEO title="Video Downloader" description="Download videos at your preferred resolution." name="Video Downloader" />
            <h1>Video Downloader</h1>
            <form className="search-section" onSubmit={getVideoInfo}>
                <div className="search-label">
                    <input type="url" placeholder="Paste a video URL" aria-label="Video URL" value={url} onChange={(event) => setUrl(event.target.value)} required />
                    <button type="button" className="paste-button" aria-label="Paste video URL" title="Paste video URL" onClick={pasteUrl} disabled={loading}>
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M9 5h6m-5-2h4a1 1 0 0 1 1 1v1h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2V4a1 1 0 0 1 1-1Z" />
                            <path d="m8 12 2 2 5-5" />
                        </svg>
                    </button>
                </div>
                <button type="submit" className="get-video-button" disabled={loading}>Get video</button>
            </form>
            {loading && (
                <div className="download-progress" role="status" aria-live="polite" aria-label={`${loadingMessage} ${downloadProgress}%`}>
                    <div className="loading-indicator">{loadingMessage}</div>
                    <div className="progress-track" aria-hidden="true">
                        <div className="progress-bar" style={{ width: `${downloadProgress}%` }} />
                    </div>
                </div>
            )}
            {error && <div className="error-message" role="alert">{error}</div>}
            {video && (
                <section className="results-section" aria-live="polite">
                    <div className="thumbnail-section">
                        {video.thumbnail && <img className="video-thumbnail" src={video.thumbnail} alt="Video thumbnail" />}
                        <div className="video-info">
                        <p><strong>Platform:</strong> {video.platform}</p>
                        <p><strong>Duration:</strong> {formatDuration(video.duration)}</p>
                    </div>
                    </div>
                    <div className="download-section">
                        <h2>{video.title}</h2>
                        <label htmlFor="resolution">Resolution</label>
                        <select id="resolution" value={resolution} onChange={(event) => setResolution(event.target.value)}>
                            <option value="">Best available</option>
                            <option value="1080">1080p</option>
                            <option value="720">720p</option>
                            <option value="480">480p</option>
                            <option value="360">360p</option>
                        </select>
                        <button type="button" className="download-button" onClick={downloadVideo} disabled={loading}>Download video</button>
                    </div>
                </section>
            )}
        </>
    );
}
