# ait - Archive of Interconnected Terms
# Run `just` to see available commands

# Default: show help
default:
    @just --list

# Build frontend and run integrated server
serve: build-web
    poetry run ait web

# Build frontend to static files and create symlink
build-web:
    cd web && npm run build
    rm -f src/ait/_static
    ln -s ../../web/build src/ait/_static

# Run API server only (for development with separate frontend)
dev-server:
    poetry run ait web --no-frontend

# Run frontend dev server with hot-reloading
dev-web:
    cd web && npm run dev

# Run type checking on frontend
check-web:
    cd web && npm run check

# Install all dependencies (Python + Node)
install:
    poetry install
    cd web && npm install

# Clean build artifacts
clean:
    rm -rf web/build web/.svelte-kit
    rm -f src/ait/_static
