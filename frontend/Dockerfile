# Stage 1: Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the Next.js application
RUN npm run build

# Stage 2: Production stage
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

# Copy built assets from the builder stage
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Set ownership for the app directory
RUN chown -R nextjs:nextjs /app

# Switch to the non-root user
USER nextjs

# Expose the port the app runs on
EXPOSE 3000

# Command to run the app
CMD ["npm", "start"] 