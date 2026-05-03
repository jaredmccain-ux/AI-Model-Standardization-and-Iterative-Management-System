# build stage
FROM node:18-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --no-package-lock --no-package-lock
COPY . .
# Fix permissions for node_modules binaries after copying all files
RUN chmod +x node_modules/.bin/*
RUN npm install --no-package-lock @rollup/rollup-linux-x64-musl -D && npm run build

# production stage
FROM nginx:alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 配置nginx
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
