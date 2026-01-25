#!/bin/bash
# Build Lambda Layer for Shared Services

set -e

LAYER_DIR="shared-services"

echo "🔨 Building Lambda Layer: $LAYER_DIR"

cd "$LAYER_DIR"

# Install dependencies to python/ directory
echo "📦 Installing dependencies..."
pip install -r requirements.txt -t python/

echo "✅ Layer built successfully!"
echo ""
echo "📋 Layer structure:"
ls -la python/

echo ""
echo "🚀 Deploy with:"
echo "sam deploy --template-file ../../conversation-storage.yaml ..."