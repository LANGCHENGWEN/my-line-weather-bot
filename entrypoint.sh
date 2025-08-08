#!/bin/bash
set -e

echo "Deploying LINE Rich Menu..."
python -m rich_menu_manager.rich_menu_deployer || echo "Rich menu deployment failed, continuing startup..."

echo "Starting application..."
exec gunicorn --bind 0.0.0.0:8080 main:app