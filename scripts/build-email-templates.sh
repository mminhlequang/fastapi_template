#!/bin/bash

# Build email templates from MJML to HTML
echo "Building email templates..."

# Check if mjml is installed
if ! command -v mjml &> /dev/null; then
    echo "MJML is not installed. Installing..."
    npm install -g mjml
fi

# Build templates
cd "$(dirname "$0")/.."
mjml app/email-templates/src/*.mjml -o app/email-templates/build/

echo "Email templates built successfully!" 