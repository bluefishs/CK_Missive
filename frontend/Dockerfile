# Stage 1: Build the React application
# node:20-alpine ships with npm 10.x which handles lockfileVersion=3 reliably
# (npm 9 in node:18-alpine has known 'Cannot read properties of undefined (reading extraneous)' bug)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy only package.json (NOT lock file)
# Reason: package-lock.json (generated on Windows host) contains platform-specific
# optional deps (@rollup/rollup-win32-*-msvc / fsevents) that trigger npm bug
# "Cannot read properties of undefined (reading 'extraneous')" on Alpine Linux.
# Regenerating from package.json inside the container produces a clean Linux lock.
COPY package.json ./

# Install dependencies including devDependencies needed for build
# - --legacy-peer-deps: bypass @vitejs/plugin-basic-ssl peer conflict (needs vite 6+, we use 5)
# - --ignore-scripts: skip husky 'prepare' hook (runs `cd .. && husky frontend/.husky` which fails in container)
RUN npm install --legacy-peer-deps --no-audit --no-fund --ignore-scripts

# Copy the rest of the application source code
COPY . .

# Inject CKProject root's shared-modules via Docker BuildKit additional_contexts
# (defined in docker-compose.production.yml frontend.build.additional_contexts).
# vite.config.ts alias '@ck-shared/ui-components' resolves to
# resolve(__dirname, '../../shared-modules/ui-components'). Since __dirname is /app
# inside the container, the target path is /shared-modules/ui-components.
COPY --from=shared-modules ui-components /shared-modules/ui-components

# Symlink frontend's node_modules so shared-modules' peerDependencies
# (react-markdown / remark-gfm / mermaid) resolve via the host project's installation.
# Without this, rollup walks from /shared-modules/ui-components/ upward and never finds
# node_modules. dev server works via vite's deeper resolution; prod build is stricter.
RUN ln -s /app/node_modules /shared-modules/node_modules

# Accept build arguments for environment variables
ARG VITE_API_BASE_URL
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}

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
# Use 127.0.0.1 (not localhost) to avoid IPv6 ::1 resolution which nginx doesn't bind.
# /nginx-health is defined in nginx.conf as a fast 200-return endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:3000/nginx-health || exit 1

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]