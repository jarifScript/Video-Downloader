import { Outlet, Link } from 'react-router-dom';
import "./MainLayout.css"; // Import the CSS file for styling

export default function MainLayout() {
    return (
        <div className="site-wrapper">
            <header>
                <nav aria-label="Main navigation">
                    <Link to="/">Home</Link>
                    <Link to="/about">About Us</Link>
                </nav>
            </header>

            {/* Semantic main tag helps crawlers find your primary content */}
            <main id="main-content">
                <Outlet /> {/* This renders the specific page content */}
            </main>

            <footer>
                <p>&copy; {new Date().getFullYear()} My Company. All rights reserved.</p>
            </footer>
        </div>
    );
}
