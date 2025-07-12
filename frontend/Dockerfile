# 1. build stage
FROM node:18-alpine AS builder
WORKDIR /app

# Copy package manifests
COPY package.json package-lock.json ./

# IMPORTANT: Remove the Windows-generated lockfile inside the container.
# This forces npm to create a dependency tree for Linux.
RUN rm package-lock.json

# Install dependencies for the correct platform
RUN npm install --omit=optional

# Grab the rest of your source code
COPY . .

# Run the production build
RUN npm run build

# 2. runtime stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]