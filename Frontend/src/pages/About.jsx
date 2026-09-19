import './About.css';

export default function About() {
    return (
        <article className="about-page">
            <header className="about-heading">
                <p className="about-eyebrow">A simpler way to download</p>
                <h1>About This Downloader</h1>
                <p className="about-intro">A lightweight tool for downloading supported public videos with a simple, clear workflow.</p>
            </header>

            <div className="about-content">
                <section className="about-section">
                    <h2>⚡ Simple. Fast. No Unnecessary Stuff.</h2>
                    <p>We built this downloader with one goal:</p>
                    <p className="about-flow">Paste a link <span aria-hidden="true">→</span> Choose your option <span aria-hidden="true">→</span> Download.</p>
                    <p>No complicated menus. No unnecessary features. Just a simple tool that does its job. Downloads are processed in the background so you can see their progress while they are being prepared.</p>
                </section>

                <section className="about-section">
                    <h2>🌐 What Can You Download?</h2>
                    <p>Download supported public videos from platforms such as:</p>
                    <p className="about-platforms">YouTube <span aria-hidden="true">•</span> Instagram <span aria-hidden="true">•</span> TikTok <span aria-hidden="true">•</span> and more</p>
                    <p>Platform support depends on what is currently supported by our underlying downloader technology and may change over time.</p>
                </section>

                <section className="about-section">
                    <h2>🔒 Privacy First</h2>
                    <p>We don't intentionally store your downloaded videos or submitted URLs.</p>
                    <p>No account required. We do not intentionally keep a personal download history or store downloaded videos permanently.</p>
                    <p>Some basic technical logs may still be created by our hosting provider.</p>
                </section>

                <section className="about-section">
                    <h2>💸 Completely Free</h2>
                    <p>This tool is free to use. The default download resolution is 720p, with other available resolutions shown when supported.</p>
                    <p>No subscription. No premium download button. No complicated plans.</p>
                </section>

                <section className="about-section">
                    <h2>📱 Made to Be Simple</h2>
                    <ul className="about-features">
                        <li>One-page experience</li>
                        <li>Clean interface</li>
                        <li>Mobile friendly</li>
                        <li>Lightweight</li>
                        <li>Easy for everyone to use</li>
                        <li>No unnecessary steps</li>
                    </ul>
                </section>

                <section className="about-section">
                    <h2>⚠️ Current Limitations</h2>
                    <p>Downloads are limited to supported public videos. Videos can be up to one hour long and up to 2 GB in size.</p>
                    <p>Some videos may be unavailable because of platform restrictions, privacy settings, regional access, changing platform rules, or limited server resources.</p>
                    <p>Processing speed can also vary depending on the video, internet connection, and current server load.</p>
                    <p>Donations help us pay for better hosting, increase download capacity, improve processing speed, raise practical limits when possible, and add support for more platforms and formats.</p>
                </section>

                <section className="about-section">
                    <h2>❤️ Support the Project</h2>
                    <p>This website runs on limited hosting resources, so downloads and processing can sometimes be slower.</p>
                    <p>If you find the tool useful, you can support the project with a small donation.</p>
                    <p>Your support can help us:</p>
                    <p className="about-support">⚡ improve speed <span aria-hidden="true">•</span> 🖥️ upgrade hosting <span aria-hidden="true">•</span> 🛠️ improve features <span aria-hidden="true">•</span> 👥 handle more users</p>
                    <p>The website will remain free.</p>
                </section>

                <section className="about-section about-section-last">
                    <h2>👨‍💻 About the Developer</h2>
                    <p>Built by an independent developer who wanted to create a simple, useful, and privacy-focused downloader without making users deal with unnecessary complexity.</p>
                    <p>Thanks for using the project! ❤️</p>
                </section>
            </div>
        </article>
    );
}