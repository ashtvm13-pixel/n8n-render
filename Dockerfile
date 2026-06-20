FROM node:22-alpine

RUN apk add --no-cache \
    tini \
    dbus \
    gnome-keyring \
    libsecret \
    curl \
    imagemagick \
    font-noto \
    font-noto-devanagari \
    fontconfig \
    && mkdir -p /run/dbus /usr/share/fonts/custom

# Install fonts via GitHub raw URLs (Google Fonts zip downloads return HTML)
RUN cd /usr/share/fonts/custom && \
    curl -sL -o CormorantGaramond-Bold.ttf \
      "https://github.com/CatharsisFonts/Cormorant/raw/master/fonts/ttf/CormorantGaramond-Bold.ttf" && \
    curl -sL -o DMSans-Regular.ttf \
      "https://github.com/google/fonts/raw/main/ofl/dmsans/static/DMSans-Regular.ttf" && \
    fc-cache -f

RUN npm install -g n8n@1.123.55 @anthropic-ai/claude-code

RUN adduser -D -h /home/node -s /bin/sh n8nuser 2>/dev/null || true

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5678

ENTRYPOINT ["/entrypoint.sh"]
