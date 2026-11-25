FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
# Valores públicos de Supabase Auth (URL y clave publishable) para el build.
ARG VITE_SUPABASE_URL=""
ARG VITE_SUPABASE_PUBLISHABLE_KEY=""
RUN VITE_SUPABASE_URL="$VITE_SUPABASE_URL" \
    VITE_SUPABASE_PUBLISHABLE_KEY="$VITE_SUPABASE_PUBLISHABLE_KEY" \
    npm run build

USER node
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--configLoader", "runner", "--host", "0.0.0.0", "--port", "5173"]
