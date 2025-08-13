/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
    outputFileTracingRoot: process.cwd(),
  },
  images: {
    domains: ['localhost', 'autoreportai.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
  },
  webpack: (config, { isServer }) => {
    // 添加 CaseSensitivePathsPlugin 来检测大小写问题
    if (!isServer) {
      const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin');
      config.plugins.push(new CaseSensitivePathsPlugin());
    }
    return config;
  },
}

module.exports = nextConfig