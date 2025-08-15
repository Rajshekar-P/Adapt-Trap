FROM node:18-slim

WORKDIR /app
ENV NODE_ENV=production

# Install dependencies with retries to avoid EAI_AGAIN
COPY package*.json ./
RUN npm config set registry https://registry.npmjs.org/ \
 && npm config set fetch-retries 5 \
 && npm config set fetch-retry-factor 2 \
 && npm config set fetch-retry-maxtimeout 600000 \
 && npm install --only=production

# App code
COPY server.js ./ 
COPY templates ./templates
COPY static ./static

# App port
ENV PORT=80
EXPOSE 80

CMD ["node", "server.js"]
