import multiprocessing

# -------------------------------
# Server Socket
# -------------------------------
bind = "0.0.0.0:3000"          # listen on all interfaces, port 3000
# Or, if you front with nginx: bind = "127.0.0.1:3000"

# -------------------------------
# Worker Processes
# -------------------------------
# formula: (2 x $CPU) + 1
workers = multiprocessing.cpu_count() * 2 + 1
# or hard-code:
# workers = 2

# -------------------------------
# SSL (if you want Gunicorn to handle HTTPS)
# -------------------------------
certfile = "cert/cert.pem"
keyfile  = "cert/key.pem"

# -------------------------------
# Timeouts & Keep-alive
# -------------------------------
timeout    = 30    # seconds to wait before killing a worker
keepalive  = 2     # seconds to hold keep-alive connections

# -------------------------------
# Preload & App Loading
# -------------------------------
preload_app = True  # load app code before workers fork

# -------------------------------
# Logging
# -------------------------------
accesslog  = "logs/gunicorn-access.log"  # "-" for stdout
errorlog   = "logs/gunicorn-error.log"   # "-" for stderr
loglevel   = "info"                      # debug, info, warning, error, critical
