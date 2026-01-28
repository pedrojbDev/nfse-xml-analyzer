/** @type {import('next').NextConfig} */
const nextConfig = {
  // Permitir chamadas para a API local
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

export default nextConfig;
