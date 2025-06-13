# infra/nginx/Dockerfile
# =========================================================
# Custom Nginx Configuration
# =========================================================
FROM nginx:1.25

# Copy custom configuration
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Expose port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]