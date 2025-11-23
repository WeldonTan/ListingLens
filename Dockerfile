FROM node:20 AS web_build
WORKDIR /app
COPY . .
RUN corepack enable && npm install -g pnpm
# We need to install dependencies for the monorepo structure if we had one, but here we just go into apps/web
WORKDIR /app/apps/web
RUN npm install
RUN npm run build
# Note: Next.js standalone output requires 'output: "standalone"' in next.config.ts/js

FROM python:3.11 AS api_build
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r apps/api/requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Install supervisor and nodejs (for the frontend server if needed, but standalone includes minimal node)
# Actually, standalone Next.js requires nodejs to run server.js
RUN apt-get update && apt-get install -y supervisor nodejs && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Frontend Build
# The standalone build is usually in .next/standalone
COPY --from=web_build /app/apps/web/.next/standalone ./web
COPY --from=web_build /app/apps/web/.next/static ./web/apps/web/.next/static
COPY --from=web_build /app/apps/web/public ./web/apps/web/public

# Copy Backend Code
COPY --from=api_build /app/apps/api ./api
# Install python dependencies again in the final image or copy site-packages
# Copying site-packages is trickier across stages if base images differ slightly. 
# Better to install requirements in final stage or use same base.
# Let's simplify: Install requirements in final stage.
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Configuration for Supervisor
COPY infra/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV API_PORT=8000

EXPOSE 3000 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
