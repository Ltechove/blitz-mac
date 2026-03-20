FROM node:20-alpine
RUN npm install -g @blitzdev/blitz-mcp
ENTRYPOINT ["blitz-mcp"]
