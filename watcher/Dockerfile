FROM alpine:latest

# Install inotify-tools for file watching and docker CLI for container management
RUN apk add --no-cache inotify-tools curl docker-cli

# Create watch script
COPY watch.sh /watch.sh
RUN chmod +x /watch.sh

CMD ["/watch.sh"]
