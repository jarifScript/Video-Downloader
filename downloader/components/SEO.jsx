import { Helmet } from 'react-helmet-async';

export default function SEO({ title, description, name, type = 'website' }) {
    return (
        <Helmet>
            {/* Standard metadata tags */}
            <title>{title} | My Awesome Site</title>
            <meta name='description' content={description} />

            {/* Open Graph / Facebook tags (Crucial for Social SEO) */}
            <meta property="og:type" content={type} />
            <meta property="og:title" content={title} />
            <meta property="og:description" content={description} />

            {/* Twitter Card tags */}
            <meta name="twitter:creator" content={name} />
            <meta name="twitter:card" content="summary_large_image" />
            <meta name="twitter:title" content={title} />
            <meta name="twitter:description" content={description} />
        </Helmet>
    );
}
