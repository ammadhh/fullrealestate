#!/bin/bash

# Navigate to the frontend directory
cd zillow-clone-frontend

# Build the frontend
npm run build

# Move the build directory up one level
mv build ..

# Go back to the parent directory
cd ..
