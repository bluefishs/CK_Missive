# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json to leverage Docker cache
COPY package*.json ./

# Install dependencies including devDependencies needed for build
RUN rm -f package-lock.json && npm install

# Copy the rest of the application source code
COPY . .

RUN ls -la

# Accept build arguments for environment variables
ARG VITE_API_BASE_URL
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}

# Debug: Print environment variables
RUN echo "Build-time VITE_API_BASE_URL: $VITE_API_BASE_URL"
RUN printenv | grep VITE

# Build the application
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:1.25-alpine AS final

# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 3000
EXPOSE 3000

# Add a healthcheck to verify Nginx is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q -O - http://localhost:3000/health || exit 1

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]