FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD wget -qO- http://127.0.0.1:3000 >/dev/null || exit 1

CMD ["npm", "run", "start", "--", "-p", "3000"]
