bind = "0.0.0.0:8000"

# The app is exposed directly from the container during local development,
# so threaded workers are more resilient to slow or half-open client sockets
# than the default sync worker.
worker_class = "gthread"
workers = 2
threads = 4
timeout = 120
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"

