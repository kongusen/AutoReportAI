// Debug: print important envs at build time
console.log('[next.config] NODE_ENV:', process.env.NODE_ENV)
console.log('[next.config] NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL)
console.log('[next.config] NEXT_PUBLIC_WS_URL:', process.env.NEXT_PUBLIC_WS_URL)

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
    const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin');
    config.plugins.push(new CaseSensitivePathsPlugin());

    // 优化 chunk 分割以防止加载错误
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization.splitChunks,
          chunks: 'async',
          cacheGroups: {
            ...config.optimization.splitChunks.cacheGroups,
            default: {
              minChunks: 2,
              priority: -20,
              reuseExistingChunk: true,
            },
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              priority: -10,
              chunks: 'all',
            },
          },
        },
      }
    }
    
    return config;
  },
}

module.exports = nextConfig